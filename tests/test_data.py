import pandas as pd

from sector_rotation.src.data import (
    fetch_ticker_data_batch,
    get_db_sector_name,
    validate_ticker_batch,
)


def test_get_db_sector_name():
    assert get_db_sector_name("Technology") == "Information Technology"
    assert get_db_sector_name("Energy") == "Energy"


def test_validate_ticker_batch_success(monkeypatch):
    sample_df = pd.DataFrame({"Close": [100.0]})
    monkeypatch.setattr(
        "sector_rotation.src.data.yf.download",
        lambda ticker, period, progress: sample_df,
    )

    ticker, valid = validate_ticker_batch("AAPL")
    assert ticker == "AAPL"
    assert valid


def test_validate_ticker_batch_failure(monkeypatch):
    monkeypatch.setattr(
        "sector_rotation.src.data.yf.download",
        lambda ticker, period, progress: pd.DataFrame(),
    )

    ticker, valid = validate_ticker_batch("BAD")
    assert ticker == "BAD"
    assert not valid


def test_fetch_ticker_data_batch(monkeypatch):
    sample_df = pd.DataFrame({"Close": [100.0], "Volume": [1000]})
    monkeypatch.setattr(
        "sector_rotation.src.data.yf.download",
        lambda ticker, period, progress: sample_df,
    )

    ticker, df = fetch_ticker_data_batch("AAPL")
    assert ticker == "AAPL"
    assert not df.empty
    assert "Close" in df.columns
    assert "Volume" in df.columns
