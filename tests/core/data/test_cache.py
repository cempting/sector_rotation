import pandas as pd
import os
import time

from sector_rotation.src.core.data.cache import (
    clear_ticker_cache,
    clear_ticker_unavailable_flag,
    get_ticker_unavailable_retry_after_seconds,
    is_ticker_temporarily_unavailable,
    load_ticker_from_cache,
    mark_ticker_temporarily_unavailable,
    save_ticker_to_cache,
)

def test_cache_roundtrip(tmp_path, monkeypatch):
    # Patch cache dir to temp
    monkeypatch.setattr("sector_rotation.src.core.data.cache.CACHE_DIR", tmp_path)
    ticker = "AAPL"
    df = pd.DataFrame({"Close": list(range(25)), "Volume": list(range(25))})
    save_ticker_to_cache(ticker, df)
    loaded = load_ticker_from_cache(ticker)
    assert loaded is not None
    assert len(loaded) == 25
    clear_ticker_cache(ticker)
    assert load_ticker_from_cache(ticker) is None


def test_cache_ignores_entries_older_than_one_day(tmp_path, monkeypatch):
    monkeypatch.setattr("sector_rotation.src.core.data.cache.CACHE_DIR", tmp_path)
    ticker = "MSFT"
    df = pd.DataFrame({"Close": list(range(25)), "Volume": list(range(25))})

    save_ticker_to_cache(ticker, df)

    from sector_rotation.src.core.data.cache import _ticker_cache_path

    path = _ticker_cache_path(ticker)
    stale_time = time.time() - (24 * 60 * 60 + 60)
    os.utime(path, (stale_time, stale_time))

    assert load_ticker_from_cache(ticker) is None


def test_ticker_unavailable_registry_roundtrip(tmp_path, monkeypatch):
    registry_file = tmp_path / "unavailable_tickers.json"
    monkeypatch.setattr("sector_rotation.src.core.data.cache.UNAVAILABLE_TICKERS_FILE", registry_file)

    mark_ticker_temporarily_unavailable("dead", reason="possibly delisted", cooldown_seconds=120)

    assert is_ticker_temporarily_unavailable("DEAD") is True
    assert get_ticker_unavailable_retry_after_seconds("DEAD") > 0

    clear_ticker_unavailable_flag("DEAD")
    assert is_ticker_temporarily_unavailable("DEAD") is False


def test_ticker_unavailable_registry_drops_expired_entries(tmp_path, monkeypatch):
    registry_file = tmp_path / "unavailable_tickers.json"
    monkeypatch.setattr("sector_rotation.src.core.data.cache.UNAVAILABLE_TICKERS_FILE", registry_file)

    registry_file.write_text(
        '{"OLD":{"until":1,"reason":"expired"},"LIVE":{"until":99999999999,"reason":"active"}}',
        encoding="utf-8",
    )

    assert is_ticker_temporarily_unavailable("OLD") is False
    assert is_ticker_temporarily_unavailable("LIVE") is True
