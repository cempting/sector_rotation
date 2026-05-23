import pandas as pd

from sector_rotation.src.features.suggestions import rendering


def test_volume_ratio_and_ma_trend_helpers():
    volume = pd.Series([100.0] * 20 + [150.0] * 20)
    close = pd.Series([float(i) for i in range(1, 220)])

    ratio = rendering._volume_ratio(volume, recent_window=20, base_window=20)
    trend_pct = rendering._ma_trend_pct(close, ma_window=50, trend_window=10)

    assert ratio > 1.0
    assert trend_pct > 0.0


def test_get_suggested_industries_filters_by_trend_and_volume(monkeypatch):
    rendering.get_suggested_industries.clear()

    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.get_universe_industries",
        lambda universe, sector=None: ["Software", "Banks"],
    )
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.get_universe_tickers",
        lambda universe, sector=None, industry=None: ["AAA", "BBB"] if industry == "Software" else ["CCC"],
    )
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.load_universe",
        lambda universe: pd.DataFrame(
            {
                "Ticker": ["AAA", "BBB", "CCC"],
                "Name": ["A", "B", "C"],
                "Sector": ["Technology", "Technology", "Financials"],
                "Industry": ["Software", "Software", "Banks"],
            }
        ),
    )

    def fake_industry_aggregate(tickers):
        if tickers == ["AAA", "BBB"]:
            close = pd.Series([100.0 + i for i in range(220)])
            volume = pd.Series([1_000_000.0] * 20 + [1_500_000.0] * 20)
            return close, volume, 2
        close = pd.Series([100.0] * 220)
        volume = pd.Series([1_000_000.0] * 40)
        return close, volume, 1

    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.compute_industry_aggregate",
        fake_industry_aggregate,
    )
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.resolve_sector_proxy_ticker",
        lambda universe, sector: None,
    )
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.resolve_industry_proxy_ticker",
        lambda universe, sector, industry: None,
    )

    suggestions = rendering.get_suggested_industries(
        "S&P 500",
        period="1y",
        industry_trend_window=10,
        volume_recent_window=20,
        volume_base_window=20,
        min_volume_ratio=1.1,
    )

    assert list(suggestions["industry"]) == ["Software"]
    assert suggestions.iloc[0]["sector"] == "Technology"
    assert suggestions.iloc[0]["volume_ratio"] > 1.0
    assert suggestions.iloc[0]["ma50_trend_pct"] > 0.0


def test_get_suggested_industries_adds_proxy_volume_assessments(monkeypatch):
    rendering.get_suggested_industries.clear()

    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.get_universe_industries",
        lambda universe, sector=None: ["Software"],
    )
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.get_universe_tickers",
        lambda universe, sector=None, industry=None: ["AAA", "BBB"],
    )
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.load_universe",
        lambda universe: pd.DataFrame(
            {
                "Ticker": ["AAA", "BBB"],
                "Name": ["A", "B"],
                "Sector": ["Technology", "Technology"],
                "Industry": ["Software", "Software"],
            }
        ),
    )

    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.compute_industry_aggregate",
        lambda tickers: (
            pd.Series([100.0 + i for i in range(220)]),
            pd.Series([1_000_000.0] * 30 + [1_400_000.0] * 20),
            2,
        ),
    )
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.resolve_sector_proxy_ticker",
        lambda universe, sector: "XLK",
    )
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.resolve_industry_proxy_ticker",
        lambda universe, sector, industry: "IGV",
    )

    def fake_fetch(ticker, force_refresh=False):
        if ticker == "XLK":
            return ticker, pd.DataFrame(
                {
                    "Close": [100.0 + i for i in range(220)],
                    "Volume": [2_000_000.0] * 200 + [2_800_000.0] * 20,
                }
            )
        if ticker == "IGV":
            return ticker, pd.DataFrame(
                {
                    "Close": [100.0 + i for i in range(220)],
                    "Volume": [1_500_000.0] * 200 + [2_250_000.0] * 20,
                }
            )
        return ticker, pd.DataFrame(
            {
                "Close": [100.0 + i for i in range(220)],
                "Volume": [1_000_000.0] * 220,
            }
        )

    monkeypatch.setattr("sector_rotation.src.features.suggestions.rendering.fetch_ticker_data_batch", fake_fetch)

    suggestions = rendering.get_suggested_industries("S&P 500")

    assert list(suggestions["industry"]) == ["Software"]
    assert suggestions.iloc[0]["sector_etf"] == "XLK"
    assert suggestions.iloc[0]["industry_etf"] == "IGV"
    assert suggestions.iloc[0]["sector_etf_volume_ratio"] > 1.0
    assert suggestions.iloc[0]["industry_etf_volume_ratio"] > 1.0


def test_get_suggested_industry_stocks_applies_all_filters(monkeypatch):
    rendering.get_suggested_industry_stocks.clear()

    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.get_universe_tickers",
        lambda universe, sector=None, industry=None: ["AAA", "BBB", "CCC"],
    )
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.get_universe_stock_name",
        lambda universe, ticker: f"Name-{ticker}",
    )

    def make_df(close_values, volume_values):
        return pd.DataFrame({"Close": pd.Series(close_values), "Volume": pd.Series(volume_values)})

    def fake_fetch(ticker, force_refresh=False):
        if ticker == "AAA":
            # Passes: MA50 trend positive, price > MA150, volume increased.
            return (
                ticker,
                make_df(
                    [100.0 + i for i in range(220)],
                    [1_000_000.0] * 20 + [1_600_000.0] * 20,
                ),
            )
        if ticker == "BBB":
            # Fails price > MA150.
            return (
                ticker,
                make_df(
                    [220.0 - i for i in range(220)],
                    [1_000_000.0] * 40,
                ),
            )
        # Fails volume increase.
        return (
            ticker,
            make_df(
                [120.0 + i for i in range(220)],
                [1_000_000.0] * 40,
            ),
        )

    monkeypatch.setattr("sector_rotation.src.features.suggestions.rendering.fetch_ticker_data_batch", fake_fetch)

    stocks = rendering.get_suggested_industry_stocks(
        "S&P 500",
        "Software",
        period="1y",
        stock_trend_window=10,
        volume_recent_window=20,
        volume_base_window=20,
        min_volume_ratio=1.1,
    )

    assert list(stocks["ticker"]) == ["AAA"]
    assert stocks.iloc[0]["name"] == "Name-AAA"
    assert stocks.iloc[0]["price"] > stocks.iloc[0]["ma150"]
    assert stocks.iloc[0]["volume_ratio"] > 1.0
    assert stocks.iloc[0]["ma50_trend_pct"] > 0.0


def test_get_suggested_industry_stocks_uses_period_fetch_for_non_default_period(monkeypatch):
    rendering.get_suggested_industry_stocks.clear()

    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.get_universe_tickers",
        lambda universe, sector=None, industry=None: ["AAA"],
    )
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.get_universe_stock_name",
        lambda universe, ticker: f"Name-{ticker}",
    )
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.fetch_ticker_data_batch",
        lambda ticker, force_refresh=False: (_ for _ in ()).throw(AssertionError("batch cache path should not be used for non-default period")),
    )

    called = {"period": None}

    def fake_fetch(ticker, period="1y"):
        called["period"] = period
        return pd.DataFrame(
            {
                "Close": pd.Series([100.0 + i for i in range(220)]),
                "Volume": pd.Series([1_000_000.0] * 20 + [1_600_000.0] * 20),
            }
        )

    monkeypatch.setattr("sector_rotation.src.features.suggestions.rendering.fetch_sector_data", fake_fetch)

    stocks = rendering.get_suggested_industry_stocks(
        "S&P 500",
        "Software",
        period="6mo",
        stock_trend_window=10,
        volume_recent_window=20,
        volume_base_window=20,
        min_volume_ratio=1.1,
    )

    assert called["period"] == "6mo"
    assert list(stocks["ticker"]) == ["AAA"]


def test_suggestions_refresh_tickers_uses_suggested_industries(monkeypatch):
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.get_suggested_industries",
        lambda universe, period, industry_trend_window, volume_recent_window, volume_base_window, min_volume_ratio: pd.DataFrame(
            {
                "industry": ["Software", "Semiconductors"],
                "sector": ["Technology", "Technology"],
                "stock_count": [2, 1],
                "ma50_trend_pct": [3.2, 2.1],
                "volume_ratio": [1.3, 1.2],
            }
        ),
    )

    def fake_tickers(universe, sector=None, industry=None):
        if industry == "Software":
            return ["MSFT", "AAPL"]
        if industry == "Semiconductors":
            return ["NVDA"]
        return ["MSFT", "AAPL", "NVDA"]

    monkeypatch.setattr("sector_rotation.src.features.suggestions.rendering.get_universe_tickers", fake_tickers)

    refresh = rendering.suggestions_refresh_tickers("S&P 500", "1y", 10, 20, 20, 1.1)

    assert refresh == ["MSFT", "AAPL", "NVDA"]


def test_suggestions_refresh_tickers_falls_back_when_no_suggestions(monkeypatch):
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.get_suggested_industries",
        lambda universe, period, industry_trend_window, volume_recent_window, volume_base_window, min_volume_ratio: pd.DataFrame(columns=["industry"]),
    )
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.get_universe_tickers",
        lambda universe, sector=None, industry=None: ["AAA", "BBB"],
    )

    refresh = rendering.suggestions_refresh_tickers("S&P 500", "1y", 10, 20, 20, 1.1)

    assert refresh == ["AAA", "BBB"]


def test_suggestions_refresh_tickers_includes_proxy_etfs(monkeypatch):
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.get_suggested_industries",
        lambda universe, period, industry_trend_window, volume_recent_window, volume_base_window, min_volume_ratio: pd.DataFrame(
            {
                "industry": ["Software"],
                "sector": ["Technology"],
                "sector_etf": ["XLK"],
                "industry_etf": ["IGV"],
                "stock_count": [2],
                "ma50_trend_pct": [3.2],
                "volume_ratio": [1.3],
                "sector_etf_volume_ratio": [1.2],
                "industry_etf_volume_ratio": [1.4],
            }
        ),
    )
    monkeypatch.setattr(
        "sector_rotation.src.features.suggestions.rendering.get_universe_tickers",
        lambda universe, sector=None, industry=None: ["MSFT", "AAPL"],
    )

    refresh = rendering.suggestions_refresh_tickers("S&P 500")

    assert refresh == ["MSFT", "AAPL", "XLK", "IGV"]
