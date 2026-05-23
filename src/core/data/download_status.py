"""Shared status tracker for external data downloads (e.g. Yahoo Finance)."""

from __future__ import annotations

from datetime import datetime, timezone
import threading

_status_lock = threading.Lock()
_status: dict[str, object] = {
    "level": "ok",
    "message": "No recent download activity.",
    "source": "",
    "updated_at": datetime.now(timezone.utc),
}

RATE_LIMIT_COOLDOWN_SECONDS = 10 * 60


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _looks_rate_limited(text: str) -> bool:
    msg = (text or "").lower()
    hints = [
        "rate limit",
        "rate-limited",
        "too many requests",
        "429",
        "try again later",
    ]
    return any(hint in msg for hint in hints)


def clear_download_status() -> None:
    with _status_lock:
        _status.update(
            {
                "level": "ok",
                "message": "No recent download activity.",
                "source": "",
                "updated_at": _now_utc(),
            }
        )


def record_download_success(message: str = "Download completed.", source: str = "yfinance") -> None:
    with _status_lock:
        # Preserve a recent rate-limit signal instead of immediately masking it.
        if _status.get("level") == "rate_limited":
            updated = _status.get("updated_at")
            if isinstance(updated, datetime) and (_now_utc() - updated).total_seconds() < 600:
                return
        _status.update(
            {
                "level": "ok",
                "message": message,
                "source": source,
                "updated_at": _now_utc(),
            }
        )


def record_download_failure(error: Exception | str, source: str = "yfinance") -> None:
    raw = str(error)
    if _looks_rate_limited(raw):
        level = "rate_limited"
        message = "Yahoo Finance rate-limited requests. Try again later."
    else:
        level = "warning"
        message = f"Data download issue: {raw}" if raw else "Data download issue occurred."

    with _status_lock:
        _status.update(
            {
                "level": level,
                "message": message,
                "source": source,
                "updated_at": _now_utc(),
            }
        )


def get_download_status(max_age_seconds: int | None = None) -> dict[str, object] | None:
    with _status_lock:
        snapshot = dict(_status)

    updated = snapshot.get("updated_at")
    if max_age_seconds is not None and isinstance(updated, datetime):
        age = (_now_utc() - updated).total_seconds()
        if age > max_age_seconds:
            return None

    if snapshot.get("level") == "rate_limited" and isinstance(updated, datetime):
        retry_after = max(0, RATE_LIMIT_COOLDOWN_SECONDS - int((_now_utc() - updated).total_seconds()))
        snapshot["retry_after_seconds"] = retry_after

    return snapshot


def is_download_blocked(source: str = "yfinance") -> bool:
    with _status_lock:
        level = _status.get("level")
        status_source = _status.get("source")
        updated = _status.get("updated_at")

    if level != "rate_limited":
        return False
    if source and status_source and source != status_source:
        return False
    if not isinstance(updated, datetime):
        return False

    age_seconds = (_now_utc() - updated).total_seconds()
    return age_seconds < RATE_LIMIT_COOLDOWN_SECONDS


def get_retry_after_seconds(source: str = "yfinance") -> int:
    if not is_download_blocked(source):
        return 0

    with _status_lock:
        updated = _status.get("updated_at")
    if not isinstance(updated, datetime):
        return 0

    age_seconds = int((_now_utc() - updated).total_seconds())
    return max(0, RATE_LIMIT_COOLDOWN_SECONDS - age_seconds)
