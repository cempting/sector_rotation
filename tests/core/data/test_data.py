import pandas as pd

from sector_rotation.src.core.data.data import (
    fetch_market_data_with_status,
    fetch_ticker_data_batch_many,
    fetch_ticker_data_batch,
    get_db_sector_name,
    validate_ticker_batch,
)
from sector_rotation.src.core.data.download_status import clear_download_status, record_download_failure


def test_get_db_sector_name():
    assert get_db_sector_name("Technology") == "Information Technology"
    assert get_db_sector_name("Energy") == "Energy"


def test_validate_ticker_batch_success(monkeypatch):
    clear_download_status()
    sample_df = pd.DataFrame({"Close": [100.0]})
    monkeypatch.setattr(
        "sector_rotation.src.core.data.data.yf.download",
        lambda ticker, period, progress: sample_df,
    )

    ticker, valid = validate_ticker_batch("AAPL")
    assert ticker == "AAPL"
    assert valid


def test_validate_ticker_batch_failure(monkeypatch):
    clear_download_status()
    monkeypatch.setattr(
        "sector_rotation.src.core.data.data.yf.download",
        lambda ticker, period, progress: pd.DataFrame(),
    )

    ticker, valid = validate_ticker_batch("BAD")
    assert ticker == "BAD"
    assert not valid


def test_fetch_ticker_data_batch(monkeypatch):
    clear_download_status()
    sample_df = pd.DataFrame({"Close": [100.0], "Volume": [1000]})
    monkeypatch.setattr(
        "sector_rotation.src.core.data.data.yf.download",
        lambda ticker, period, progress: sample_df,
    )

    ticker, df = fetch_ticker_data_batch("AAPL")
    assert ticker == "AAPL"
    assert not df.empty
    assert "Close" in df.columns
    assert "Volume" in df.columns


def test_fetch_ticker_data_batch_many_downloads_missing_in_one_batch(monkeypatch):
    clear_download_status()
    saved = []

    def fake_cache_load(ticker):
        return None

    def fake_cache_save(ticker, df):
        saved.append(ticker)

    def fake_download(tickers, period, progress, group_by, threads):
        idx = pd.date_range("2024-01-01", periods=3)
        cols = pd.MultiIndex.from_product(
            [["AAA", "BBB"], ["Close", "Volume"]],
            names=["Ticker", "Field"],
        )
        data = [
            [100.0, 1_000.0, 200.0, 2_000.0],
            [101.0, 1_100.0, 201.0, 2_100.0],
            [102.0, 1_200.0, 202.0, 2_200.0],
        ]
        return pd.DataFrame(data, index=idx, columns=cols)

    monkeypatch.setattr("sector_rotation.src.core.data.data.load_ticker_from_cache", fake_cache_load)
    monkeypatch.setattr("sector_rotation.src.core.data.data.save_ticker_to_cache", fake_cache_save)
    monkeypatch.setattr("sector_rotation.src.core.data.data.yf.download", fake_download)

    result = fetch_ticker_data_batch_many(["AAA", "BBB"], force_refresh=False)

    assert set(result.keys()) == {"AAA", "BBB"}
    assert "Close" in result["AAA"].columns
    assert "Volume" in result["BBB"].columns
    assert sorted(saved) == ["AAA", "BBB"]


def test_fetch_ticker_data_batch_many_skips_network_when_rate_limited(monkeypatch):
    clear_download_status()
    record_download_failure("429 Too Many Requests")

    def fake_cache_load(ticker):
        return None

    def fail_download(*args, **kwargs):
        raise AssertionError("yfinance should not be called during cooldown")

    monkeypatch.setattr("sector_rotation.src.core.data.data.load_ticker_from_cache", fake_cache_load)
    monkeypatch.setattr("sector_rotation.src.core.data.data.yf.download", fail_download)

    result = fetch_ticker_data_batch_many(["AAA", "BBB"], force_refresh=False)

    assert set(result.keys()) == {"AAA", "BBB"}
    assert result["AAA"].empty
    assert result["BBB"].empty

    clear_download_status()


def test_fetch_market_data_with_status_marks_live_source(monkeypatch):
    clear_download_status()
    sample_df = pd.DataFrame({"Close": [100.0], "Volume": [1_000.0]})

    monkeypatch.setattr(
        "sector_rotation.src.core.data.data.load_ticker_from_cache",
        lambda ticker: None,
    )
    monkeypatch.setattr(
        "sector_rotation.src.core.data.data.yf.download",
        lambda ticker, period, progress: sample_df,
    )

    data, status = fetch_market_data_with_status(["AAPL"], period="1d", force_refresh=True, use_cache=False)

    assert "AAPL" in data
    assert not data["AAPL"].empty
    assert status["AAPL"]["source"] == "live"
    assert status["AAPL"]["label"] == "Live (up to date)"


def test_fetch_market_data_with_status_uses_stale_cache_when_blocked(monkeypatch):
    clear_download_status()
    record_download_failure("429 Too Many Requests")
    stale_df = pd.DataFrame({"Close": [100.0], "Volume": [1_000.0]})

    monkeypatch.setattr(
        "sector_rotation.src.core.data.data.load_ticker_from_cache",
        lambda ticker: None,
    )
    monkeypatch.setattr(
        "sector_rotation.src.core.data.data.load_ticker_from_cache_any_age",
        lambda ticker: stale_df,
    )
    monkeypatch.setattr(
        "sector_rotation.src.core.data.data.get_ticker_cache_age_seconds",
        lambda ticker: 7200,
    )
    monkeypatch.setattr(
        "sector_rotation.src.core.data.data.yf.download",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network should stay blocked")),
    )

    data, status = fetch_market_data_with_status(["AAPL"], force_refresh=False, use_cache=True)

    assert "AAPL" in data
    assert not data["AAPL"].empty
    assert status["AAPL"]["source"] == "cache_stale"
    assert status["AAPL"]["is_stale"] is True
    assert "out of date" in str(status["AAPL"]["label"]).lower()

    clear_download_status()


def test_fetch_market_data_with_status_skips_unavailable_ticker_download(monkeypatch):
    clear_download_status()

    def fail_download(*args, **kwargs):
        raise AssertionError("network should not be called for unavailable cooldown tickers")

    monkeypatch.setattr(
        "sector_rotation.src.core.data.data.is_ticker_temporarily_unavailable",
        lambda ticker: ticker == "DEAD",
    )
    monkeypatch.setattr(
        "sector_rotation.src.core.data.data.get_ticker_unavailable_retry_after_seconds",
        lambda ticker: 600,
    )
    monkeypatch.setattr("sector_rotation.src.core.data.data.yf.download", fail_download)

    data, status = fetch_market_data_with_status(["DEAD"], force_refresh=False, use_cache=True)

    assert "DEAD" in data
    assert data["DEAD"].empty
    assert status["DEAD"]["source"] == "unavailable_cooldown"
    assert "retry" in str(status["DEAD"]["label"]).lower()


def test_fetch_market_data_with_status_marks_unavailable_after_retry_failure(monkeypatch):
    clear_download_status()

    calls = {"count": 0}

    def fake_download(*args, **kwargs):
        calls["count"] += 1
        return pd.DataFrame()

    marked: list[str] = []

    monkeypatch.setattr(
        "sector_rotation.src.core.data.data.is_ticker_temporarily_unavailable",
        lambda ticker: False,
    )
    monkeypatch.setattr(
        "sector_rotation.src.core.data.data.mark_ticker_temporarily_unavailable",
        lambda ticker, reason, cooldown_seconds: marked.append(ticker),
    )
    monkeypatch.setattr(
        "sector_rotation.src.core.data.data.get_ticker_unavailable_retry_after_seconds",
        lambda ticker: 3600,
    )
    monkeypatch.setattr("sector_rotation.src.core.data.data.load_ticker_from_cache", lambda ticker: None)
    monkeypatch.setattr("sector_rotation.src.core.data.data.yf.download", fake_download)

    data, status = fetch_market_data_with_status(["ZZZZ"], force_refresh=False, use_cache=True)

    assert "ZZZZ" in data
    assert data["ZZZZ"].empty
    assert status["ZZZZ"]["source"] == "unavailable_cooldown"
    assert marked == ["ZZZZ"]
    assert calls["count"] >= 2
