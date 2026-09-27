"""SQLite access for campus_customs.db, shared by the API routes and the agent tools."""

import json
import os
import sqlite3
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
HW4_DIR = BACKEND_DIR.parent


def find_data_dir() -> Path:
    """Use CAMPUS_DATA_DIR if set, else data/ (assignment path), else data-2/."""
    if os.getenv("CAMPUS_DATA_DIR"):
        return Path(os.environ["CAMPUS_DATA_DIR"]).resolve()
    for name in ("data", "data-2"):
        candidate = HW4_DIR / name
        if (candidate / "campus_customs.db").exists():
            return candidate
    raise RuntimeError("Could not find campus_customs.db in data/ or data-2/")


DATA_DIR = find_data_dir()
DB_PATH = DATA_DIR / "campus_customs.db"

SIZE_ORDER = "CASE size WHEN 'XS' THEN 0 WHEN 'S' THEN 1 WHEN 'M' THEN 2 WHEN 'L' THEN 3 WHEN 'XL' THEN 4 WHEN 'XXL' THEN 5 ELSE 6 END"


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


SIZES = ["XS", "S", "M", "L", "XL", "XXL"]

# Shopper-friendly categories, derived from the catalogue's free-text garment_type (checked in this order).
CATEGORY_RULES = [
    ("T-shirts", ("t-shirt", "tee")),
    ("Hoodies", ("hood",)),
    ("Quarter-zips", ("quarter-zip", "1 4 zip", "1/4 zip")),
    ("Fleece & jackets", ("fleece", "jacket")),
    ("Crewnecks", ("crewneck", "crew")),
]


def category_of(garment_type: str, name: str) -> str:
    text = f"{garment_type} {name}".lower()
    for category, keywords in CATEGORY_RULES:
        if any(k in text for k in keywords):
            return category
    return "Other tops"


def product_from_row(row: sqlite3.Row) -> dict:
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "description": row["description"],
        "colors": json.loads(row["colors"]),
        "search_tags": json.loads(row["search_tags"]),
        "image_url": f"/media/{row['image_file_path']}",
        "price": row["price"],
        "category": category_of(row["garment_type"], row["name"]),
    }


def list_products() -> list[dict]:
    """Every catalogue product with its total stock and which sizes are in stock."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock,
                   GROUP_CONCAT(CASE WHEN i.quantity > 0 THEN i.size END) AS sizes_in_stock
            FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id
            GROUP BY c.product_id
            ORDER BY c.name
            """
        ).fetchall()
    products = []
    for r in rows:
        in_stock = set((r["sizes_in_stock"] or "").split(","))
        products.append({**product_from_row(r), "total_stock": r["total_stock"],
                         "sizes_in_stock": [s for s in SIZES if s in in_stock]})
    return products


def get_product(product_id: str) -> dict | None:
    """One product with per-size stock, or None if the ID doesn't exist."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            return None
        sizes = conn.execute(
            f"SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY {SIZE_ORDER}",
            (product_id,),
        ).fetchall()
    inventory = [{"size": s["size"], "quantity": s["quantity"]} for s in sizes]
    return {
        **product_from_row(row),
        "inventory": inventory,
        "total_stock": sum(s["quantity"] for s in inventory),
    }


# --- Chat history (logged-in users only) -------------------------------------

def get_customer(user_id: int) -> dict | None:
    """Non-sensitive profile fields for the chat agent (never the password hash)."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, first_name, last_name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    if row is None:
        return None
    first, last = row["first_name"], row["last_name"]
    if not first:  # older rows may only have the combined name
        first, _, last = row["name"].partition(" ")
    return {"id": row["id"], "first_name": first, "last_name": last or "", "email": row["email"],
            "member_since": row["created_at"][:10]}


def load_chat_messages(user_id: int, limit: int = 50) -> list[dict]:
    """The user's most recent chat messages, oldest first."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content, products_json, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    messages = []
    for r in reversed(rows):
        extra = json.loads(r["products_json"]) if r["products_json"] else None
        # Older rows store a plain list of products; newer rows store {"products": [...], "results": {...}}.
        if isinstance(extra, list):
            extra = {"products": extra, "results": None}
        extra = extra or {"products": [], "results": None}
        messages.append({"role": r["role"], "content": r["content"], "products": extra.get("products") or [],
                         "results": extra.get("results"), "created_at": r["created_at"]})
    return messages


def save_chat_turn(user_id: int, user_message: str, reply: str, extra: dict) -> None:
    """Store one user message and the assistant's reply (with the cards it showed) together."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)", (user_id, user_message)
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply, json.dumps(extra)),
        )


def clear_chat_messages(user_id: int) -> int:
    with get_db() as conn:
        return conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,)).rowcount
