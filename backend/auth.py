"""Create-account / login / logout for Campus Customs.

Passwords are hashed with PBKDF2-HMAC-SHA256 and a random per-user salt; plaintext
passwords are never stored or logged. Logged-in state is an HttpOnly cookie holding
a signed token (user id + expiry + HMAC signature).
"""

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

HASH_ALGO = "pbkdf2_sha256"
NEW_ITERATIONS = 600_000  # OWASP recommendation for PBKDF2-SHA256
LEGACY_ITERATIONS = 120_000  # used by the seeded users (hash format has no iteration field)
MIN_PASSWORD_LENGTH = 8

SESSION_COOKIE = "cc_session"
SESSION_TTL_SECONDS = 7 * 24 * 3600
# Set SESSION_SECRET in .env to keep people logged in across restarts; otherwise a fresh
# random secret is made at startup (restarting the server logs everyone out).
SESSION_SECRET = os.getenv("SESSION_SECRET", "").encode() or secrets.token_bytes(32)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --- Password hashing -------------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), NEW_ITERATIONS).hex()
    return f"{HASH_ALGO}${NEW_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) == 4:  # pbkdf2_sha256$iterations$salt$hash (new accounts)
        algo, iterations, salt, expected = parts[0], int(parts[1]), parts[2], parts[3]
    elif len(parts) == 3:  # pbkdf2_sha256$salt$hash (seeded accounts)
        algo, salt, expected = parts
        iterations = LEGACY_ITERATIONS
    else:
        return False
    if algo != HASH_ALGO:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return hmac.compare_digest(digest, expected)


# --- Session tokens ---------------------------------------------------------

def _sign(payload: str) -> str:
    return hmac.new(SESSION_SECRET, payload.encode(), hashlib.sha256).hexdigest()


def make_session_token(user_id: int) -> str:
    payload = f"{user_id}.{int(time.time()) + SESSION_TTL_SECONDS}"
    return f"{payload}.{_sign(payload)}"


def read_session_token(token: str | None) -> int | None:
    if not token or token.count(".") != 2:
        return None
    user_id, expires, signature = token.split(".")
    if not hmac.compare_digest(signature, _sign(f"{user_id}.{expires}")):
        return None
    if int(expires) < time.time():
        return None
    return int(user_id)


def current_user_id(request: Request) -> int | None:
    """ID of the logged-in user for this request, or None."""
    return read_session_token(request.cookies.get(SESSION_COOKIE))


# --- Routes -----------------------------------------------------------------

class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def public_user(row: sqlite3.Row) -> dict:
    """User info that's safe to send to the browser (never the password hash)."""
    first, last = row["first_name"], row["last_name"]
    if not first:  # older rows may only have the combined name
        first, _, last = row["name"].partition(" ")
    return {"id": row["id"], "first_name": first, "last_name": last, "email": row["email"]}


def build_router(get_db) -> APIRouter:
    router = APIRouter(prefix="/api/auth")

    def set_session(response: Response, user_id: int) -> None:
        response.set_cookie(
            SESSION_COOKIE,
            make_session_token(user_id),
            max_age=SESSION_TTL_SECONDS,
            httponly=True,  # JavaScript can't read it
            samesite="lax",
        )

    @router.post("/signup", status_code=201)
    def signup(req: SignupRequest, response: Response):
        first, last = req.first_name.strip(), req.last_name.strip()
        email = req.email.strip().lower()
        if not first or not last:
            raise HTTPException(400, "First and last name are required.")
        if not EMAIL_RE.match(email):
            raise HTTPException(400, "Please enter a valid email address.")
        if len(req.password) < MIN_PASSWORD_LENGTH:
            raise HTTPException(400, f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

        with get_db() as conn:
            try:
                cur = conn.execute(
                    "INSERT INTO users (name, first_name, last_name, email, password_hash) VALUES (?, ?, ?, ?, ?)",
                    (f"{first} {last}", first, last, email, hash_password(req.password)),
                )
            except sqlite3.IntegrityError:
                raise HTTPException(409, "An account with that email already exists.")
            row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
        set_session(response, row["id"])
        return public_user(row)

    @router.post("/login")
    def login(req: LoginRequest, response: Response):
        email = req.email.strip().lower()
        with get_db() as conn:
            row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()
        # Same message whether the email or the password was wrong.
        if row is None or not verify_password(req.password, row["password_hash"]):
            raise HTTPException(401, "Incorrect email or password.")
        set_session(response, row["id"])
        return public_user(row)

    @router.post("/logout")
    def logout(response: Response):
        response.delete_cookie(SESSION_COOKIE)
        return {"ok": True}

    @router.get("/me")
    def me(request: Request):
        user_id = current_user_id(request)
        if user_id is None:
            raise HTTPException(401, "Not logged in.")
        with get_db() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(401, "Not logged in.")
        return public_user(row)

    return router
