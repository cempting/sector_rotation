import pandas as pd
import os
from sector_rotation.src.cache import load_ticker_from_cache, save_ticker_to_cache, clear_ticker_cache

def test_cache_roundtrip(tmp_path, monkeypatch):
    # Patch cache dir to temp
    monkeypatch.setattr("sector_rotation.src.cache.CACHE_DIR", tmp_path)
    ticker = "AAPL"
    df = pd.DataFrame({"Close": list(range(25)), "Volume": list(range(25))})
    save_ticker_to_cache(ticker, df)
    loaded = load_ticker_from_cache(ticker)
    assert loaded is not None
    assert len(loaded) == 25
    clear_ticker_cache(ticker)
    assert load_ticker_from_cache(ticker) is None
