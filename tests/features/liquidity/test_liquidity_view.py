import pandas as pd

from sector_rotation.src.features.liquidity.rendering import (
    _collect_sector_rows_all_markets,
    build_flow_edges,
    classify_liquidity_regime,
    compute_liquidity_scores,
    get_market_sentiment_snapshot,
    liquidity_refresh_tickers,
)


def test_compute_liquidity_scores_returns_sorted_frame():
    rows = [
        {"label": "A", "ticker": "AAA", "bucket": "Risk", "ret_20": 0.10, "ret_5": 0.03, "vol_jump": 1.3},
        {"label": "B", "ticker": "BBB", "bucket": "Rates", "ret_20": -0.05, "ret_5": -0.01, "vol_jump": 0.9},
        {"label": "C", "ticker": "CCC", "bucket": "Metals", "ret_20": 0.02, "ret_5": 0.01, "vol_jump": 1.1},
    ]

    df = compute_liquidity_scores(rows)

    assert list(df.columns) == ["label", "ticker", "bucket", "ret_20", "ret_5", "vol_jump", "liquidity"]
    assert df.iloc[0]["liquidity"] >= df.iloc[-1]["liquidity"]


def test_collect_sector_rows_all_markets_aggregates_same_sector(monkeypatch):
    sample = pd.DataFrame(
        {
            "Close": pd.Series([100 + i for i in range(80)]),
            "Volume": pd.Series([1_000_000 + i for i in range(80)]),
        }
    )

    monkeypatch.setattr("sector_rotation.src.features.liquidity.rendering.list_universes", lambda: ["S&P 500", "ASX 200"])
    monkeypatch.setattr("sector_rotation.src.features.liquidity.rendering.get_universe_sectors", lambda u: ["Technology"]) 
    monkeypatch.setattr(
        "sector_rotation.src.features.liquidity.rendering.resolve_sector_proxy_ticker",
        lambda u, s: "XLK" if u == "S&P 500" else "^AXNJ",
    )
    monkeypatch.setattr("sector_rotation.src.features.liquidity.rendering.fetch_sector_data", lambda t, period="1y": sample)

    rows = _collect_sector_rows_all_markets(
        period="1y",
        long_lookback=20,
        short_lookback=5,
        volume_recent=5,
        volume_base=20,
    )

    assert len(rows) == 1
    assert rows[0]["label"] == "Technology"
    assert rows[0]["market_count"] == 2
    assert "S&P 500" in rows[0]["members"]
    assert "ASX 200" in rows[0]["members"]


def test_build_flow_edges_pairs_outflows_to_inflows():
    nodes = pd.DataFrame(
        {
            "label": ["Out1", "Out2", "In1", "In2"],
            "ticker": ["A", "B", "C", "D"],
            "bucket": ["Risk", "Risk", "Rates", "Metals"],
            "liquidity": [-20.0, -10.0, 25.0, 15.0],
            "ret_20": [0.0, 0.0, 0.0, 0.0],
            "ret_5": [0.0, 0.0, 0.0, 0.0],
            "vol_jump": [1.0, 1.0, 1.0, 1.0],
        }
    )

    edges = build_flow_edges(nodes, max_edges=2)

    assert len(edges) == 2
    assert edges[0]["from"] == "Out1"
    assert edges[0]["to"] == "In1"


def test_classify_liquidity_regime_risk_on_and_off():
    risk_on_nodes = pd.DataFrame(
        {
            "label": ["Risk", "Markets", "Rates", "Metals"],
            "ticker": ["A", "B", "C", "D"],
            "bucket": ["Risk", "Markets", "Rates", "Metals"],
            "liquidity": [20.0, 15.0, -5.0, -2.0],
            "ret_20": [0.0, 0.0, 0.0, 0.0],
            "ret_5": [0.0, 0.0, 0.0, 0.0],
            "vol_jump": [1.0, 1.0, 1.0, 1.0],
        }
    )
    risk_off_nodes = pd.DataFrame(
        {
            "label": ["Risk", "Markets", "Rates", "Metals", "Cash", "FX"],
            "ticker": ["A", "B", "C", "D", "E", "F"],
            "bucket": ["Risk", "Markets", "Rates", "Metals", "Cash", "FX"],
            "liquidity": [-15.0, -10.0, 12.0, 9.0, 8.0, 7.0],
            "ret_20": [0.0] * 6,
            "ret_5": [0.0] * 6,
            "vol_jump": [1.0] * 6,
        }
    )

    assert classify_liquidity_regime(risk_on_nodes) == "Risk-On"
    assert classify_liquidity_regime(risk_off_nodes) == "Risk-Off"


def test_get_market_sentiment_snapshot_shape(monkeypatch):
    base = pd.DataFrame(
        {
            "Close": pd.Series([100 + i for i in range(260)]),
            "Volume": pd.Series([1_000_000 + i * 1000 for i in range(260)]),
        }
    )

    monkeypatch.setattr(
        "sector_rotation.src.features.liquidity.rendering.fetch_sector_data",
        lambda ticker, period="1y": base,
    )

    snapshot = get_market_sentiment_snapshot(period="1y")

    assert "sentiment" in snapshot
    assert "fear_greed" in snapshot
    assert "vix" in snapshot
    assert 0 <= snapshot["fear_greed"] <= 100


def test_liquidity_refresh_tickers_includes_vix_and_proxies(monkeypatch):
    monkeypatch.setattr("sector_rotation.src.features.liquidity.rendering.get_universe_sectors", lambda u: ["Technology"])
    monkeypatch.setattr("sector_rotation.src.features.liquidity.rendering.resolve_sector_proxy_ticker", lambda u, s: "XLK")
    monkeypatch.setattr("sector_rotation.src.features.liquidity.rendering.get_sector_industry_counts", lambda u, s: {"Software": 3})
    monkeypatch.setattr("sector_rotation.src.features.liquidity.rendering.get_universe_tickers", lambda u, sector=None, industry=None: ["MSFT", "AAPL"])

    tickers = liquidity_refresh_tickers("S&P 500", "Technology")

    assert "^VIX" in tickers
    assert "SPY" in tickers
    assert "XLK" in tickers


def test_liquidity_refresh_tickers_all_markets_scans_all_universes(monkeypatch):
    monkeypatch.setattr("sector_rotation.src.features.liquidity.rendering.list_universes", lambda: ["S&P 500", "ASX 200"])
    monkeypatch.setattr(
        "sector_rotation.src.features.liquidity.rendering.get_universe_sectors",
        lambda u: ["Technology"] if u == "S&P 500" else ["Materials"],
    )
    monkeypatch.setattr(
        "sector_rotation.src.features.liquidity.rendering.resolve_sector_proxy_ticker",
        lambda u, s: "XLK" if u == "S&P 500" else "^AXMJ",
    )

    tickers = liquidity_refresh_tickers("S&P 500", "Technology", all_markets=True)

    assert "XLK" in tickers
    assert "^AXMJ" in tickers
    assert "^VIX" in tickers
