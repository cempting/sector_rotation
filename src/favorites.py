import json
from pathlib import Path

from .cache import CACHE_DIR

FAVORITES_FILE = CACHE_DIR / "favorites.json"


def _read_all() -> dict[str, list[str]]:
    if not FAVORITES_FILE.exists():
        return {}
    try:
        data = json.loads(FAVORITES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

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


def _write_all(data: dict[str, list[str]]) -> None:
    FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)
    FAVORITES_FILE.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


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
