import pandas as pd
import os
import time

from sector_rotation.src.core.data.cache import load_ticker_from_cache, save_ticker_to_cache, clear_ticker_cache

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
