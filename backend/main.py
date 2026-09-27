"""Campus Customs API: products, images, auth, and the shop chatbot.

Run from the backend/ folder:
    ../.venv/bin/uvicorn main:app --reload --port 8000
"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic_ai.exceptions import ModelHTTPError

import database
from agent import history_from_saved, run_chat
from auth import build_router, current_user_id
from models import ChatRequest, ChatResponse, CustomerInfo, StoredChatMessage
from tools import find_alternatives

log = logging.getLogger("campus_customs")

HISTORY_TURNS_FOR_AGENT = 20  # saved messages sent to the agent as memory
HISTORY_MESSAGES_FOR_UI = 50  # saved messages shown when the chat reopens

BLOCKED_REPLY = (
    "Sorry, I can't help with that. I'm here for Campus Customs shopping: "
    "products, sizes, stock, and gift ideas. What can I help you find?"
)

app = FastAPI(title="Campus Customs API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
# Image paths in the DB look like "products/foo.jpg", so they're served at /media/products/foo.jpg
app.mount("/media", StaticFiles(directory=database.DATA_DIR), name="media")
app.include_router(build_router(database.get_db))


@app.get("/api/health")
def health():
    return {"status": "ok", "db": str(database.DB_PATH.relative_to(database.HW4_DIR))}


@app.get("/api/products")
def list_products():
    return database.list_products()


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    product = database.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def current_customer(request: Request) -> tuple[int, CustomerInfo] | None:
    """(user_id, profile) for the logged-in shopper, or None for guests."""
    user_id = current_user_id(request)
    if user_id is None:
        return None
    profile = database.get_customer(user_id)
    if profile is None:
        return None
    return user_id, CustomerInfo(**{k: profile[k] for k in CustomerInfo.model_fields})


@app.get("/api/products/{product_id}/alternatives")
def product_alternatives(product_id: str, size: str | None = None, limit: int = 4):
    """Similar in-stock products (same logic as the agent's find_alternatives tool), as product cards."""
    result = find_alternatives(product_id, size=size, limit=limit)
    if isinstance(result, str):
        raise HTTPException(status_code=404, detail="Product not found")
    cards = []
    for alt in result.alternatives:
        p = database.get_product(alt.product_id)
        cards.append({**p, "size_quantity": alt.size_quantity, "why": alt.why})
    return {"requested_size": result.requested_size, "alternatives": cards}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    logged_in = current_customer(request)
    if logged_in:
        # Logged-in memory comes from the database, not from whatever the browser sends.
        user_id, customer = logged_in
        history = history_from_saved(database.load_chat_messages(user_id, HISTORY_TURNS_FOR_AGENT))
    else:
        user_id, customer, history = None, None, req.history
    try:
        response = await run_chat(req.message, history, customer, req.page, user_id)
    except ModelHTTPError as e:
        # The model gateway's content filter blocked the message (e.g. a jailbreak attempt).
        # Blocked turns aren't saved, so they don't get re-sent as history and block later messages.
        if "content_filter" in str(e.body):
            log.warning("Chat message blocked by content filter")
            return ChatResponse(reply=BLOCKED_REPLY, blocked=True)
        log.exception("Chat agent failed")
        raise HTTPException(503, "The shop assistant is having trouble right now. Please try again in a moment.")
    except Exception:
        log.exception("Chat agent failed")
        raise HTTPException(503, "The shop assistant is having trouble right now. Please try again in a moment.")

    if user_id is not None:
        database.save_chat_turn(
            user_id,
            req.message,
            response.reply,
            {
                "products": [c.model_dump() for c in response.products],
                "results": response.results.model_dump() if response.results else None,
            },
        )
    return response


@app.get("/api/chat/history", response_model=list[StoredChatMessage])
def chat_history(request: Request):
    """Saved chat for the logged-in shopper (guests get an empty list)."""
    logged_in = current_customer(request)
    if not logged_in:
        return []
    return database.load_chat_messages(logged_in[0], HISTORY_MESSAGES_FOR_UI)


@app.delete("/api/chat/history")
def clear_chat_history(request: Request):
    logged_in = current_customer(request)
    if not logged_in:
        raise HTTPException(401, "Not logged in.")
    return {"deleted": database.clear_chat_messages(logged_in[0])}
