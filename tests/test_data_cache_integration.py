import pandas as pd
import os
import time

from sector_rotation.src.data.data import fetch_ticker_data_batch
from sector_rotation.src.data.cache import clear_ticker_cache

def test_fetch_ticker_data_batch_uses_cache(monkeypatch):
    ticker = "AAPL"
    # Clear cache first
    clear_ticker_cache(ticker)
    # Patch yf.download to count calls
    calls = {}
    def fake_download(ticker, period, progress):
        calls["count"] = calls.get("count", 0) + 1
        return pd.DataFrame({"Close": list(range(25)), "Volume": list(range(25))})
    monkeypatch.setattr("sector_rotation.src.data.data.yf.download", fake_download)
    # First call: should call yf
    t, df1 = fetch_ticker_data_batch(ticker, force_refresh=True)
    assert calls["count"] == 1
    # Second call: should use cache
    t, df2 = fetch_ticker_data_batch(ticker, force_refresh=False)
    assert calls["count"] == 1
    # Third call: force refresh again
    t, df3 = fetch_ticker_data_batch(ticker, force_refresh=True)
    assert calls["count"] == 2


def test_fetch_ticker_data_batch_refreshes_stale_cache(monkeypatch, tmp_path):
    monkeypatch.setattr("sector_rotation.src.data.cache.CACHE_DIR", tmp_path)
    ticker = "AAPL"
    calls = {}

    def fake_download(ticker, period, progress):
        calls["count"] = calls.get("count", 0) + 1
        return pd.DataFrame({"Close": list(range(25)), "Volume": list(range(25))})

    monkeypatch.setattr("sector_rotation.src.data.data.yf.download", fake_download)

    t, df1 = fetch_ticker_data_batch(ticker, force_refresh=True)
    assert calls["count"] == 1

    from sector_rotation.src.data.cache import _ticker_cache_path

    path = _ticker_cache_path(ticker)
    stale_time = time.time() - (24 * 60 * 60 + 60)
    os.utime(path, (stale_time, stale_time))

    t, df2 = fetch_ticker_data_batch(ticker, force_refresh=False)
    assert calls["count"] == 2
