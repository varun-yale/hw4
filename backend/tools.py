"""Tools the Campus Customs agent can call. All product facts come from the database."""

import re

import database
from models import (
    Alternative,
    AlternativeResults,
    ProductDetails,
    ProductSummary,
    SearchResults,
    SizeStock,
    StockCheck,
    StockStatus,
)

TOKEN_RE = re.compile(r"[a-z0-9]+")
LOW_STOCK_THRESHOLD = 5

SIZE_ALIASES = {
    "xs": "XS", "extra small": "XS", "x small": "XS", "xsmall": "XS",
    "s": "S", "small": "S", "sm": "S",
    "m": "M", "medium": "M", "med": "M",
    "l": "L", "large": "L", "lg": "L",
    "xl": "XL", "extra large": "XL", "x large": "XL", "xlarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xx large": "XXL", "2x": "XXL", "extra extra large": "XXL", "double xl": "XXL",
}


# Different words shoppers and the catalogue use for the same kind of garment.
SYNONYMS = {"hood": "hoodie", "hooded": "hoodie", "hoody": "hoodie"}
# Words that describe many garment kinds; ignored in garment_type when a more specific word is given.
GENERIC_GARMENT_WORDS = {"sweatshirt", "pullover", "top", "sleeve", "short", "long"}


PHRASES = [
    (re.compile(r"\b1\s*/?\s*4(?=[\s-]*zip)"), "quarter"),  # "1/4 zip", "1 4 Zip" -> "quarter zip"
    (re.compile(r"\bcrew[\s-]+neck\b"), "crewneck"),
    (re.compile(r"\b(tees?|tshirts?)\b"), "t-shirt"),
]


def _tokens(text: str) -> set[str]:
    text = text.lower()
    for pattern, replacement in PHRASES:
        text = pattern.sub(replacement, text)
    words = TOKEN_RE.findall(text)
    # Treat simple plurals like "hoodies" / "shirts" the same as the singular.
    words = [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words]
    return {SYNONYMS.get(w, w) for w in words}


def _normalize_size(size: str) -> str:
    key = " ".join(TOKEN_RE.findall(size.lower().replace("-", " ")))
    return SIZE_ALIASES.get(key, size.strip().upper())


def _status(quantity: int) -> StockStatus:
    if quantity <= 0:
        return "out_of_stock"
    return "low_stock" if quantity <= LOW_STOCK_THRESHOLD else "in_stock"


def _find_product(product: str) -> dict | None:
    """Look up by exact product_id, falling back to the product name (e.g. "Morse Logo T-Shirt")."""
    p = database.get_product(product.strip())
    if p:
        return p
    slug = "-".join(TOKEN_RE.findall(product.lower()))
    p = database.get_product(slug)
    if p:
        return p
    for candidate in database.list_products():
        if "-".join(TOKEN_RE.findall(candidate["name"].lower())) == slug:
            return database.get_product(candidate["product_id"])
    return None


def _not_found(product: str) -> str:
    return f"No product matches {product!r}. Use search_products to find the right product_id."


def _summary(p: dict) -> ProductSummary:
    return ProductSummary(
        product_id=p["product_id"],
        name=p["name"],
        garment_type=p["garment_type"],
        colors=p["colors"],
        price=p["price"],
        total_stock=p["total_stock"],
    )


def search_products(
    query: str = "",
    garment_type: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    in_stock_only: bool = False,
    limit: int = 30,
) -> SearchResults | str:
    """Search the Campus Customs catalogue.

    Args:
        query: Keywords like "hockey", "Morse college", "vintage bulldog", or "gift for mom". Leave empty to browse.
        garment_type: Optional kind of item, e.g. "hoodie", "crewneck", "t-shirt", "1/4 zip", "fleece".
        color: Optional color to filter by, e.g. "navy", "gray", "white".
        max_price: Optional maximum price in dollars.
        in_stock_only: If true, skip products with no stock in any size.
        limit: Maximum number of results to return (1-30).
    """
    limit = max(1, min(limit, 30))
    products = database.list_products()
    haystacks = {
        p["product_id"]: _tokens(" ".join([p["name"], p["garment_type"], p["description"], *p["colors"], *p["search_tags"]]))
        for p in products
    }
    # Words on most products ("yale", "campus") don't narrow anything, so ignore them.
    query_tokens = {
        t for t in _tokens(query) if sum(t in h for h in haystacks.values()) <= len(products) // 2
    }
    garment_tokens = _tokens(garment_type or "")
    garment_tokens = (garment_tokens - GENERIC_GARMENT_WORDS) or garment_tokens
    results: list[tuple[int, dict]] = []
    for p in products:
        # Every word of the garment type must match, so "t-shirt" doesn't pull in "performance shirt".
        if garment_tokens and not (garment_tokens <= _tokens(f"{p['garment_type']} {p['name']}")):
            continue
        if color and not any(color.lower() in c.lower() for c in p["colors"]):
            continue
        if max_price is not None and p["price"] > max_price:
            continue
        if in_stock_only and p["total_stock"] == 0:
            continue
        score = len(query_tokens & haystacks[p["product_id"]])
        if query_tokens and score == 0:
            continue
        results.append((score, p))
    if not results:
        return "No products matched these filters. If the shopper asked for something specific, the shop likely doesn't carry it; say so and suggest something close."
    results.sort(key=lambda item: -item[0])
    # Nothing narrowed the search, or it matched more than fit on the page: better to ask than to dump everything.
    unfiltered = not (query_tokens or garment_tokens or color or max_price is not None)
    return SearchResults(
        total_matches=len(results),
        products=[_summary(p) for _, p in results[:limit]],
        too_broad=unfiltered or len(results) > 30,
    )


def get_product_details(product_id: str) -> ProductDetails | str:
    """Get full details for one product: description, colors, current price, and stock for every size.

    Args:
        product_id: The product_id from a search result (a product name also works).
    """
    p = _find_product(product_id)
    if p is None:
        return _not_found(product_id)
    inventory = [SizeStock(size=s["size"], quantity=s["quantity"], status=_status(s["quantity"])) for s in p["inventory"]]
    return ProductDetails(
        **_summary(p).model_dump(),
        description=p["description"],
        search_tags=p["search_tags"],
        inventory=inventory,
        in_stock_sizes=[s.size for s in inventory if s.quantity > 0],
        sold_out_sizes=[s.size for s in inventory if s.quantity == 0],
    )


def check_stock(product_id: str, size: str | None = None) -> StockCheck | str:
    """Check current price and stock for a product, optionally for one specific size.

    Use this whenever a shopper asks if something is available, how many are left, or about a size.

    Args:
        product_id: The product_id from a search result (a product name also works).
        size: Optional size the shopper asked about, e.g. "M", "medium", "XL", "2XL".
    """
    p = _find_product(product_id)
    if p is None:
        return _not_found(product_id)
    by_size = {s["size"]: s["quantity"] for s in p["inventory"]}
    in_stock = [s for s, q in by_size.items() if q > 0]
    sold_out = [s for s, q in by_size.items() if q == 0]
    requested = _normalize_size(size) if size else None
    if requested is None:
        quantity, offered = p["total_stock"], True
    else:
        offered = requested in by_size
        quantity = by_size.get(requested, 0)
    return StockCheck(
        product_id=p["product_id"],
        name=p["name"],
        price=p["price"],
        requested_size=requested,
        size_offered=offered,
        quantity=quantity,
        status=_status(quantity),
        in_stock_sizes=in_stock,
        sold_out_sizes=sold_out,
        total_stock=p["total_stock"],
    )


def find_alternatives(
    product_id: str,
    size: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    limit: int = 4,
) -> AlternativeResults | str:
    """Find similar products that ARE available, for when an item or size is sold out, or a color/size isn't offered.

    Results are ranked by similarity (same category, shared themes like sport/college, colors, similar price)
    and only include products in stock in the requested size (and color, if given).

    Args:
        product_id: The product the shopper wanted (product_id or name).
        size: The size they need, e.g. "XL" or "medium". Alternatives must have it in stock.
        color: Optional color they want, e.g. "pink" or "gray". Alternatives must come in it.
        max_price: Optional budget in dollars.
        limit: How many alternatives to return (1-6).
    """
    original = _find_product(product_id)
    if original is None:
        return _not_found(product_id)
    requested = _normalize_size(size) if size else None
    limit = max(1, min(limit, 6))
    products = database.list_products()

    def theme_tokens(p: dict) -> set[str]:
        return {tok for tok in _tokens(" ".join([p["name"], *p["search_tags"]])) if len(tok) > 2}

    themes = {p["product_id"]: theme_tokens(p) for p in products}
    doc_freq: dict[str, int] = {}
    for toks in themes.values():
        for tok in toks:
            doc_freq[tok] = doc_freq.get(tok, 0) + 1
    # Words on lots of products ("yale", "hoodie") say little; rare shared words (a sport, a college) say a lot.
    common = {tok for tok, n in doc_freq.items() if n > len(products) // 4}
    original_themes = theme_tokens(original) - common
    original_category = database.category_of(original["garment_type"], original["name"])

    scored: list[tuple[float, dict, list[str]]] = []
    for p in products:
        if p["product_id"] == original["product_id"]:
            continue
        if requested and requested not in p["sizes_in_stock"]:
            continue
        if not requested and p["total_stock"] == 0:
            continue
        if color and not any(color.lower() in c.lower() for c in p["colors"]):
            continue
        if max_price is not None and p["price"] > max_price:
            continue
        reasons, score = [], 0.0
        if p["category"] == original_category:
            score += 6
            reasons.append(f"also {original_category.lower()}")
        shared = sorted(original_themes & (themes[p["product_id"]] - common), key=lambda tok: doc_freq[tok])
        if shared:
            score += min(sum(3 if doc_freq[tok] <= 8 else 1 for tok in shared), 9)
            reasons.append("shares " + ", ".join(shared[:3]))
        shared_colors = {c.lower() for c in p["colors"]} & {c.lower() for c in original["colors"]}
        score += 0.5 * len(shared_colors)
        score -= abs(p["price"] - original["price"]) / 20
        reasons.append("same price" if p["price"] == original["price"] else f"${p['price']:.0f}")
        scored.append((score, p, reasons))
    scored.sort(key=lambda s: -s[0])

    alternatives = []
    for _, p, reasons in scored[:limit]:
        qty = None
        if requested:
            qty = next(s["quantity"] for s in database.get_product(p["product_id"])["inventory"] if s["size"] == requested)
        alternatives.append(Alternative(**_summary(p).model_dump(), category=p["category"], size_quantity=qty,
                                        why="; ".join(reasons)))
    return AlternativeResults(
        original_product_id=original["product_id"],
        original_name=original["name"],
        requested_size=requested,
        requested_color=color,
        other_sizes_in_stock=[s["size"] for s in original["inventory"] if s["quantity"] > 0],
        alternatives=alternatives,
    )


def list_garment_types() -> dict[str, int]:
    """List every kind of garment the shop sells, with how many products of each kind."""
    counts: dict[str, int] = {}
    for p in database.list_products():
        counts[p["garment_type"]] = counts.get(p["garment_type"], 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


SHOP_TOOLS = [search_products, get_product_details, check_stock, find_alternatives, list_garment_types]
