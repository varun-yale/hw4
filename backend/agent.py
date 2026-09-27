"""Campus Customs shop agent: loads the system prompt and model, wires in the tools, runs a chat turn."""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # skip the Logfire ad in server logs

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext, capture_run_messages
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

import database
from audit import RunRecorder, stop_reason_for
from models import (
    AgentReply,
    ChatHistoryMessage,
    ChatResponse,
    CustomerInfo,
    PageContext,
    ProductCard,
    ProductResults,
    ViewedProduct,
)
from tools import SHOP_TOOLS

BACKEND_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BACKEND_DIR / "prompts" / "prompt.md"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
# Hard caps per shopper message, so a confused model can't loop (cost + response time).
USAGE_LIMITS = UsageLimits(request_limit=8, tool_calls_limit=16)

# The API key lives in the repo-root .env (AI-Foundation/.env); HW4/.env also works.
for env_path in (BACKEND_DIR.parent / ".env", BACKEND_DIR.parent.parent / ".env"):
    if env_path.exists():
        load_dotenv(env_path)


@dataclass
class ShopDeps:
    """Per-request context the agent can see: who is chatting and what's on their screen."""

    customer: CustomerInfo | None = None  # None for guests
    page: PageContext | None = None
    viewed_product: ViewedProduct | None = None  # product open on a detail page (checked against the DB)


def build_model() -> OpenAIResponsesModel:
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is missing from .env")
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={
            "x-portkey-api-key": api_key,
            "x-portkey-provider": os.getenv("PORTKEY_PROVIDER", "openai"),
        },
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


@lru_cache(maxsize=1)
def get_agent() -> Agent[ShopDeps, AgentReply]:
    """Build the agent once, on the first chat request."""
    agent = Agent(
        build_model(),
        deps_type=ShopDeps,
        output_type=AgentReply,
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        tools=SHOP_TOOLS,
        retries=2,
    )

    @agent.instructions
    def customer_context(ctx: RunContext[ShopDeps]) -> str:
        c = ctx.deps.customer
        if c is None:
            return "## Current shopper\nA guest (not logged in). Their chat isn't saved after they leave."
        return (
            "## Current shopper\n"
            f"Logged in as {c.first_name} {c.last_name} ({c.email}), member since {c.member_since}. "
            "Earlier messages in this conversation are their saved chat history from previous visits."
        )

    @agent.instructions
    def page_context(ctx: RunContext[ShopDeps]) -> str:
        page, viewed = ctx.deps.page, ctx.deps.viewed_product
        if viewed:
            return (
                "## What's on the shopper's screen\n"
                f"They are viewing the product page for **{viewed.name}** (product_id `{viewed.product_id}`). "
                'Words like "this", "it", or "this one" refer to that product unless they clearly mean something else. '
                "Look it up with your tools before answering about it."
            )
        if page and page.results_title:
            return (
                "## What's on the shopper's screen\n"
                f'The Products page is showing your earlier search results: "{page.results_title}".'
            )
        if page:
            return f"## What's on the shopper's screen\nThey are on the {page.path} page (no specific product open)."
        return ""

    return agent


def to_model_history(history: list[ChatHistoryMessage]) -> list[ModelMessage]:
    """Turn the widget's earlier messages into PydanticAI message history."""
    messages: list[ModelMessage] = []
    for turn in history:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


def history_from_saved(messages: list[dict]) -> list[ChatHistoryMessage]:
    """Saved chat_messages rows -> agent history, noting which products each reply showed."""
    turns = []
    for m in messages:
        shown = (m.get("results") or {}).get("products") or m.get("products") or []
        content = m["content"]
        if shown:
            listed = "; ".join(f"{i}. {p['name']} ({p['product_id']})" for i, p in enumerate(shown, 1))
            content += f"\n[Products shown: {listed}]"
        turns.append(ChatHistoryMessage(role=m["role"], content=content[:4000]))
    return turns


async def run_chat(
    message: str,
    history: list[ChatHistoryMessage],
    customer: CustomerInfo | None = None,
    page: PageContext | None = None,
    user_id: int | None = None,
) -> ChatResponse:
    viewed = None
    if page and page.product_id and (p := database.get_product(page.product_id)):
        viewed = ViewedProduct(product_id=p["product_id"], name=p["name"])
    recorder = RunRecorder(message, len(history), user_id, page, MODEL_NAME)
    with capture_run_messages() as run_messages:
        try:
            result = await get_agent().run(
                message,
                deps=ShopDeps(customer=customer, page=page, viewed_product=viewed),
                message_history=to_model_history(history),
                usage_limits=USAGE_LIMITS,
            )
        except Exception as error:
            recorder.finish(run_messages, stop_reason_for(error))
            raise
    response = build_response(result.output)
    usage = result.usage() if callable(result.usage) else result.usage  # method in some PydanticAI versions
    recorder.finish(result.new_messages(), "completed", usage=usage, response=response)
    return response


def build_response(output: AgentReply) -> ChatResponse:
    """Turn the agent's structured output into what the site receives."""
    # Only show cards for products that really exist, with data straight from the database.
    cards: list[ProductCard] = []
    for product_id in dict.fromkeys(output.product_ids):
        p = database.get_product(product_id)
        if p:
            cards.append(ProductCard(**{k: p[k] for k in ProductCard.model_fields}))

    # Search/browse answers go on the page; single-product answers stay as small cards in the chat.
    suggestions = [s.strip()[:40] for s in output.suggestions if s.strip()][:4]
    if output.results_title and cards:
        return ChatResponse(
            reply=output.reply, results=ProductResults(title=output.results_title, products=cards), suggestions=suggestions
        )
    return ChatResponse(reply=output.reply, products=cards, suggestions=suggestions)
