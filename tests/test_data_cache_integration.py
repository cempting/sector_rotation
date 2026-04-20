import pandas as pd
from sector_rotation.src.data import fetch_ticker_data_batch
from sector_rotation.src.cache import clear_ticker_cache

def test_fetch_ticker_data_batch_uses_cache(monkeypatch):
    ticker = "AAPL"
    # Clear cache first
    clear_ticker_cache(ticker)
    # Patch yf.download to count calls
    calls = {}
    def fake_download(ticker, period, progress):
        calls["count"] = calls.get("count", 0) + 1
        return pd.DataFrame({"Close": list(range(25)), "Volume": list(range(25))})
    monkeypatch.setattr("sector_rotation.src.data.yf.download", fake_download)
    # First call: should call yf
    t, df1 = fetch_ticker_data_batch(ticker, force_refresh=True)
    assert calls["count"] == 1
    # Second call: should use cache
    t, df2 = fetch_ticker_data_batch(ticker, force_refresh=False)
    assert calls["count"] == 1
    # Third call: force refresh again
    t, df3 = fetch_ticker_data_batch(ticker, force_refresh=True)
    assert calls["count"] == 2
