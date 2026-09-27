"""Append-only audit trail of agent runs, stored in output/audit_trail.json.

Every chat message produces one AuditEntry: who asked (guest / user id only), which page they were on,
each tool call with its arguments and a short result summary, token usage, and why the run stopped.
Entries are only ever added; existing entries are never edited or removed. Text fields are scrubbed
of emails, card/phone-like numbers, password hashes, and key-like strings before they're written.
"""

import fcntl
import json
import logging
import os
import re
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart

from database import HW4_DIR
from models import AlternativeResults, AuditEntry, AuditToolCall, ChatResponse, ProductDetails, SearchResults, StockCheck

AUDIT_PATH = Path(os.getenv("AUDIT_TRAIL_PATH", HW4_DIR / "output" / "audit_trail.json"))
PREVIEW_CHARS = 160
ARG_CHARS = 80

log = logging.getLogger("campus_customs.audit")
_lock = threading.Lock()

# Things that must never end up in the audit file.
_REDACTIONS = [
    (re.compile(r"pbkdf2_sha256\$[^\s\"']+"), "[password-hash]"),
    (re.compile(r"\b(sk|pk|rk)[-_][A-Za-z0-9_-]{12,}\b"), "[api-key]"),
    (re.compile(r"\b(?=[A-Za-z0-9+/_]*\d)[A-Za-z0-9+/_]{32,}={0,2}"), "[secret]"),  # long key-like tokens (not hyphenated ids)
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"),
    (re.compile(r"\b\d(?:[ -]?\d){11,18}\b"), "[number]"),  # card-like numbers
    (re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*\S+"), r"\1: [redacted]"),
]


def redact(text: str, limit: int = PREVIEW_CHARS) -> str:
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _clean_args(args: dict[str, Any]) -> dict[str, Any]:
    return {k: redact(v, ARG_CHARS) if isinstance(v, str) else v for k, v in args.items()}


def summarize_result(content: Any) -> str:
    """One line describing a tool result, without dumping the whole payload."""
    if isinstance(content, SearchResults):
        broad = ", too broad" if content.too_broad else ""
        return f"{content.total_matches} matches, returned {len(content.products)}{broad}"
    if isinstance(content, StockCheck):
        size = content.requested_size or "all sizes"
        offered = "" if content.size_offered else ", size not offered"
        return f"{content.name} {size}: qty {content.quantity} ({content.status}{offered}), ${content.price:.2f}"
    if isinstance(content, ProductDetails):
        return f"{content.name}: ${content.price:.2f}, in stock {','.join(content.in_stock_sizes) or 'none'}"
    if isinstance(content, AlternativeResults):
        names = ", ".join(a.name for a in content.alternatives[:3])
        return f"{len(content.alternatives)} alternatives in {content.requested_size or 'any size'}: {names}"
    if isinstance(content, dict):
        return f"{len(content)} garment types"
    if isinstance(content, BaseModel):
        return type(content).__name__
    return redact(str(content), 120)


def extract_tool_calls(messages: list[ModelMessage]) -> list[AuditToolCall]:
    """Pair each tool call with its result (or retry/failure) from a run's messages."""
    calls: dict[str, dict] = {}
    order: list[str] = []
    for message in messages:
        for part in message.parts:
            if isinstance(message, ModelResponse) and isinstance(part, ToolCallPart):
                if part.tool_name == "final_result":  # structured output, not a real tool
                    continue
                calls[part.tool_call_id] = {"tool_name": part.tool_name, "arguments": _clean_args(part.args_as_dict()),
                                            "result_summary": "no result (run stopped)", "outcome": "failed"}
                order.append(part.tool_call_id)
            elif isinstance(message, ModelRequest) and isinstance(part, ToolReturnPart) and part.tool_call_id in calls:
                calls[part.tool_call_id].update(result_summary=summarize_result(part.content), outcome="success")
            elif isinstance(message, ModelRequest) and isinstance(part, RetryPromptPart) and part.tool_call_id in calls:
                calls[part.tool_call_id].update(result_summary=redact(str(part.content), 120), outcome="retried")
    return [AuditToolCall(step=i, **calls[cid]) for i, cid in enumerate(order, 1)]


def stop_reason_for(error: Exception) -> str:
    body = str(getattr(error, "body", "")) + str(error)
    if "content_filter" in body:
        return "blocked_by_content_filter"
    if type(error).__name__ == "UsageLimitExceeded":
        return "usage_limit_exceeded"
    return f"error:{type(error).__name__}"


class RunRecorder:
    """Collects facts about one agent run, then appends one AuditEntry."""

    def __init__(self, message: str, history_turns: int, user_id: int | None, page, model: str, task: str = "shop_chat"):
        self.started = time.monotonic()
        self.base = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "run_id": uuid.uuid4().hex[:12],
            "task": task,
            "shopper": {"type": "logged_in" if user_id is not None else "guest", "user_id": user_id},
            "page": {"path": getattr(page, "path", None), "viewed_product_id": getattr(page, "product_id", None)},
            "message_preview": redact(message),
            "history_turns": history_turns,
            "model": model,
        }

    def finish(self, messages: list[ModelMessage], stop_reason: str, usage=None, response: ChatResponse | None = None) -> None:
        try:  # auditing must never break the chat
            self._write(messages, stop_reason, usage, response)
        except Exception:
            log.exception("Could not write audit entry")

    def _write(self, messages, stop_reason, usage, response) -> None:
        output = {}
        if response is not None:
            cards = response.results.products if response.results else response.products
            output = {
                "reply_preview": redact(response.reply),
                "products_shown": len(cards),
                "shown_on": "products_page" if response.results else ("chat" if cards else "none"),
                "results_title": response.results.title if response.results else None,
                "suggestions": len(response.suggestions),
            }
        entry = AuditEntry(
            **self.base,
            tool_calls=extract_tool_calls(messages),
            model_requests=getattr(usage, "requests", 0) or 0,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            output=output,
            duration_ms=int((time.monotonic() - self.started) * 1000),
            stop_reason=stop_reason,
        )
        append_entry(entry)


def append_entry(entry: AuditEntry) -> None:
    """Add one entry to the JSON array without touching existing entries."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_path = AUDIT_PATH.with_suffix(".lock")
    with _lock, open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)  # also safe across processes
        entries: list = []
        if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size > 0:
            try:
                entries = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
                if not isinstance(entries, list):
                    raise ValueError("audit trail is not a JSON list")
            except ValueError:
                # Never overwrite a damaged file: set it aside and start a new one.
                AUDIT_PATH.rename(AUDIT_PATH.with_name(f"audit_trail.corrupt-{int(time.time())}.json"))
                entries = []
        entries.append(entry.model_dump(mode="json"))
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=AUDIT_PATH.parent, delete=False, suffix=".tmp") as tmp:
            json.dump(entries, tmp, indent=2)
            tmp.write("\n")
        Path(tmp.name).replace(AUDIT_PATH)  # atomic: readers see the old or new file, never half of one
