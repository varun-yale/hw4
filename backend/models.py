"""Pydantic types for the chat API and the PydanticAI agent's structured output."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class PageContext(BaseModel):
    """Where the shopper is on the site when they send a message."""

    path: str = Field(default="/", max_length=200, description="Current URL path, e.g. /products/morse-1-4-zip")
    product_id: str | None = Field(default=None, max_length=120, description="Product open on a detail page")
    results_title: str | None = Field(default=None, max_length=80, description="Chat results shown on /products")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000, description="What the shopper just typed")
    history: list[ChatHistoryMessage] = Field(
        default_factory=list,
        max_length=20,
        description="Earlier turns (guests only; logged-in history is loaded from the database)",
    )
    page: PageContext | None = None


class CustomerInfo(BaseModel):
    """What the agent knows about a logged-in shopper. Never includes the password hash."""

    first_name: str
    last_name: str
    email: str
    member_since: str = Field(description="Account creation date, YYYY-MM-DD")


class ViewedProduct(BaseModel):
    """The product open on the shopper's screen, confirmed against the database."""

    product_id: str
    name: str


MAX_RESULT_PRODUCTS = 30


class AgentReply(BaseModel):
    """What the agent returns for each turn."""

    reply: str = Field(description="Friendly answer to show the shopper, in plain text (no markdown tables)")
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=MAX_RESULT_PRODUCTS,
        description="product_id values (from tool results only) of the products the reply recommends, discusses, "
        "or found in a search, best matches first; empty if none",
    )
    suggestions: list[str] = Field(
        default_factory=list,
        max_length=4,
        description="Up to 4 short quick-reply options the shopper can tap (each under 30 characters), e.g. "
        "['Hoodies', 'T-shirts', 'Under $50']. Use them with a clarifying question or to offer next steps; "
        "each must make sense as the shopper's next message.",
    )
    results_title: str | None = Field(
        default=None,
        max_length=60,
        description="Short heading for a search/browse result set, e.g. 'Hoodies' or 'Gray crewnecks under $60'. "
        "Set it only when product_ids are search results that should be shown on the page; "
        "leave null for questions about one specific product (price, stock, details).",
    )


class ProductCard(BaseModel):
    """Everything the site needs to draw a product card (same fields as the Products page cards)."""

    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    price: float
    image_url: str
    total_stock: int


class ProductResults(BaseModel):
    """A set of search results the site shows as product cards on the page."""

    title: str = Field(description="Heading shown above the cards")
    products: list[ProductCard]


class ChatResponse(BaseModel):
    """What POST /api/chat returns to the site."""

    reply: str = Field(description="Chat bubble text")
    products: list[ProductCard] = Field(
        default_factory=list, description="Products the reply is about (shown as small cards in the chat)"
    )
    results: ProductResults | None = Field(
        default=None, description="Search results to put on the page; null if this reply shouldn't change the page"
    )
    suggestions: list[str] = Field(default_factory=list, description="Quick-reply chips shown under the reply")
    blocked: bool = Field(
        default=False, description="True if the content filter blocked the message; the turn isn't saved or re-sent"
    )


class StoredChatMessage(BaseModel):
    """One saved message returned by GET /api/chat/history."""

    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    results: ProductResults | None = None
    created_at: str


class ProductSummary(BaseModel):
    """Compact product info returned by the search tool."""

    product_id: str
    name: str
    garment_type: str
    colors: list[str]
    price: float
    total_stock: int


StockStatus = Literal["in_stock", "low_stock", "out_of_stock"]


class SearchResults(BaseModel):
    """What search_products returns."""

    total_matches: int = Field(description="How many products matched in total")
    products: list[ProductSummary] = Field(description="The matches, best first (at most `limit`)")
    too_broad: bool = Field(
        default=False,
        description="True if the search had no real filter or matched over 30 products; ask a clarifying question",
    )


class SizeStock(BaseModel):
    size: str = Field(description="Size label: XS, S, M, L, XL, or XXL")
    quantity: int = Field(description="Units on hand in this size, straight from the inventory table")
    status: StockStatus = Field(description="out_of_stock if 0, low_stock if 1-5, otherwise in_stock")


class ProductDetails(ProductSummary):
    """Full product info returned by the details tool."""

    description: str
    search_tags: list[str]
    inventory: list[SizeStock] = Field(description="Stock for every size, smallest to largest")
    in_stock_sizes: list[str] = Field(description="Sizes with at least 1 unit")
    sold_out_sizes: list[str] = Field(description="Sizes with 0 units")


class StockCheck(BaseModel):
    """Answer to "is this product (in this size) available?" returned by check_stock."""

    product_id: str
    name: str
    price: float = Field(description="Current price in dollars from the catalogue")
    requested_size: str | None = Field(description="Normalized size asked about (e.g. 'medium' -> 'M'), or None")
    size_offered: bool = Field(description="False if the product is never made in the requested size")
    quantity: int = Field(description="Units in the requested size, or total units across sizes if no size asked")
    status: StockStatus = Field(description="Status of the requested size, or of the product overall")
    in_stock_sizes: list[str] = Field(description="Sizes that can be bought right now, to suggest alternatives")
    sold_out_sizes: list[str]
    total_stock: int = Field(description="Units across all sizes")


class Alternative(ProductSummary):
    """An in-stock substitute found by find_alternatives."""

    category: str
    size_quantity: int | None = Field(description="Units in the requested size (None if no size was requested)")
    why: str = Field(description="Short reason it's similar, e.g. 'also a Yale hoodie, same $68 price'")


class AlternativeResults(BaseModel):
    """What find_alternatives returns."""

    original_product_id: str
    original_name: str
    requested_size: str | None
    requested_color: str | None
    other_sizes_in_stock: list[str] = Field(description="Sizes of the original product that are still in stock")
    alternatives: list[Alternative] = Field(description="Similar products available in the requested size/color")


# --- Audit trail (output/audit_trail.json) ------------------------------------

class AuditToolCall(BaseModel):
    """One tool call the agent made during a run."""

    step: int = Field(description="Order of the call within the run, starting at 1")
    tool_name: str
    arguments: dict = Field(description="Arguments the model passed (redacted, long values trimmed)")
    result_summary: str = Field(description="One-line summary of what the tool returned")
    outcome: Literal["success", "failed", "retried"]


class AuditEntry(BaseModel):
    """One agent run (one shopper message). Appended to the audit trail, never edited."""

    timestamp: str = Field(description="UTC time the run started, ISO 8601")
    run_id: str
    task: str = Field(description="What kind of agent run this was, e.g. shop_chat")
    shopper: dict = Field(description="guest or logged_in, plus the internal user id (no name/email)")
    page: dict = Field(description="Page path and viewed product id, if any")
    message_preview: str = Field(description="Start of the shopper's message, with emails/numbers redacted")
    history_turns: int = Field(description="How many earlier chat turns the agent was given")
    model: str
    tool_calls: list[AuditToolCall]
    model_requests: int = Field(description="LLM calls in this run (cost/speed indicator)")
    input_tokens: int
    output_tokens: int
    output: dict = Field(description="Reply preview, cards shown, results title, number of quick replies")
    duration_ms: int
    stop_reason: str = Field(description="completed, blocked_by_content_filter, usage_limit_exceeded, or error:<Type>")
