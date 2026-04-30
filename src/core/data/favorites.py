import json
from pathlib import Path

from .cache import CACHE_DIR

FAVORITES_FILE = CACHE_DIR / "favorites.json"


def _normalize_favorites_data(data: object) -> dict[str, list[str]]:
    if not isinstance(data, dict):
        return {}

    normalized: dict[str, list[str]] = {}
    for universe, tickers in data.items():
        if not isinstance(universe, str) or not isinstance(tickers, list):
            continue
        cleaned = []
        seen = set()
        for t in tickers:
            if not isinstance(t, str):
                continue
            ticker = t.strip().upper()
            if ticker and ticker not in seen:
                seen.add(ticker)
                cleaned.append(ticker)
        normalized[universe] = cleaned
    return normalized


def _read_all() -> dict[str, list[str]]:
    if not FAVORITES_FILE.exists():
        return {}
    try:
        data = json.loads(FAVORITES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

    return _normalize_favorites_data(data)


def _write_all(data: dict[str, list[str]]) -> None:
    FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)
    FAVORITES_FILE.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def export_favorites_settings() -> str:
    """Export favorites settings as JSON text."""
    return json.dumps(_read_all(), indent=2, sort_keys=True)


def import_favorites_settings(payload: str | bytes, merge: bool = False) -> tuple[int, int]:
    """Import favorites settings from JSON text/bytes.

    Returns (universe_count, ticker_count) after applying the import.
    """
    try:
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        incoming_raw = json.loads(payload)
    except Exception as exc:
        raise ValueError("Invalid favorites JSON payload") from exc

    incoming = _normalize_favorites_data(incoming_raw)
    if not isinstance(incoming_raw, dict):
        raise ValueError("Favorites payload must be a JSON object")

    if merge:
        existing = _read_all()
        merged: dict[str, list[str]] = {}
        for universe in set(existing.keys()) | set(incoming.keys()):
            tickers = []
            seen = set()
            for ticker in existing.get(universe, []) + incoming.get(universe, []):
                if ticker not in seen:
                    seen.add(ticker)
                    tickers.append(ticker)
            if tickers:
                merged[universe] = tickers
        _write_all(merged)
        applied = merged
    else:
        _write_all(incoming)
        applied = incoming

    return len(applied), sum(len(tickers) for tickers in applied.values())


def list_favorites(universe: str) -> list[str]:
    return list(_read_all().get(universe, []))


def list_all_favorites() -> dict[str, list[str]]:
    """Return favorites grouped by universe."""
    return _read_all()


def total_favorites_count() -> int:
    """Return total favorites count across all universes."""
    all_favorites = _read_all()
    return sum(len(tickers) for tickers in all_favorites.values())


def is_favorite(universe: str, ticker: str) -> bool:
    t = ticker.strip().upper()
    if not t:
        return False
    return t in _read_all().get(universe, [])


def add_favorite(universe: str, ticker: str) -> bool:
    t = ticker.strip().upper()
    if not t:
        return False

    data = _read_all()
    items = data.setdefault(universe, [])
    if t in items:
        return False
    items.append(t)
    _write_all(data)
    return True


def remove_favorite(universe: str, ticker: str) -> bool:
    t = ticker.strip().upper()
    if not t:
        return False

    data = _read_all()
    items = data.get(universe, [])
    if t not in items:
        return False

    items.remove(t)
    if items:
        data[universe] = items
    else:
        data.pop(universe, None)
    _write_all(data)
    return True


def toggle_favorite(universe: str, ticker: str) -> bool:
    if is_favorite(universe, ticker):
        remove_favorite(universe, ticker)
        return False
    add_favorite(universe, ticker)
    return True
