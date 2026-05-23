import pandas as pd
import numpy as np

from sector_rotation.src.renderers import (
    render_data_card,
    safe_format,
    _compute_return_vol_rr,
    _compute_stock_metrics,
    _format_fundamental,
    _news_topic,
)
from sector_rotation.src.charts import get_trend_colors
from sector_rotation.src.core.ui.view_components import render_stock_details_panel


def test_safe_format_numeric_and_nan():
    assert safe_format(3.14159) == "3.14"
    assert safe_format(float("nan")) == "N/A"


def test_format_fundamental_none_and_nan():
    """Test _format_fundamental with None and NaN values."""
    assert _format_fundamental(None) == "N/A"
    assert _format_fundamental(float("nan")) == "N/A"
    assert _format_fundamental(pd.NA) == "N/A"


def test_format_fundamental_percentage():
    """Test _format_fundamental with percentage flag."""
    assert _format_fundamental(0.05, is_pct=True) == "5.0%"
    assert _format_fundamental(0.2534, is_pct=True) == "25.3%"
    assert _format_fundamental(0.0, is_pct=True) == "0.0%"


def test_format_fundamental_billions():
    """Test _format_fundamental formats billions correctly."""
    assert _format_fundamental(1e9) == "$1.0B"
    assert _format_fundamental(2.5e9) == "$2.5B"
    assert _format_fundamental(150e9) == "$150.0B"


def test_format_fundamental_millions():
    """Test _format_fundamental formats millions correctly."""
    assert _format_fundamental(1e6) == "$1.0M"
    assert _format_fundamental(500e6) == "$500.0M"
    assert _format_fundamental(999e6) == "$999.0M"


def test_format_fundamental_small_values():
    """Test _format_fundamental with small numeric values."""
    assert _format_fundamental(12.34) == "12.34"
    assert _format_fundamental(0.5) == "0.50"
    assert _format_fundamental(1.5) == "1.50"


def test_format_fundamental_invalid_input():
    """Test _format_fundamental with invalid inputs."""
    assert _format_fundamental("invalid") == "N/A"
    assert _format_fundamental([1, 2, 3]) == "N/A"


def test_compute_stock_metrics_empty_dataframe():
    """Test _compute_stock_metrics with empty DataFrame."""
    df = pd.DataFrame()
    metrics = _compute_stock_metrics(df, "AAPL")
    # Should have fundamental metrics keys even with empty price data
    assert "market_cap" in metrics or len(metrics) == 0


def test_compute_stock_metrics_price_data_only():
    """Test _compute_stock_metrics with price data but no fundamentals."""
    # Create sample price data
    dates = pd.date_range("2024-01-01", periods=100)
    df = pd.DataFrame({
        "Close": np.linspace(100, 120, 100),
        "Volume": np.random.randint(1000000, 5000000, 100),
    }, index=dates)

    metrics = _compute_stock_metrics(df, "TEST")

    # Verify technical metrics are computed
    assert "latest" in metrics
    assert "change_20d_pct" in metrics
    assert "ma50" in metrics
    assert "ma150" in metrics
    assert "volatility_20d" in metrics

    # Verify values are reasonable
    assert metrics["latest"] == df["Close"].iloc[-1]
    assert isinstance(metrics["change_20d_pct"], (int, float))
    assert isinstance(metrics["volatility_20d"], (int, float))
    assert "liq_trend_3m_pct" in metrics
    assert "liq_trend_6m_pct" in metrics
    assert "liq_accel_weekly_pct" in metrics
    assert "volume_ratio_20_60" in metrics
    assert "liq_context" in metrics


def test_compute_stock_metrics_ma_calculation():
    """Test moving average calculations in _compute_stock_metrics."""
    dates = pd.date_range("2024-01-01", periods=200)
    prices = np.linspace(100, 150, 200)
    df = pd.DataFrame({
        "Close": prices,
        "Volume": 1000000,
    }, index=dates)

    metrics = _compute_stock_metrics(df, "TEST")

    # 50-day MA should be calculated correctly
    expected_ma50 = df["Close"].rolling(50).mean().iloc[-1]
    assert abs(metrics["ma50"] - expected_ma50) < 0.01

    # 150-day MA should be calculated correctly
    expected_ma150 = df["Close"].rolling(150).mean().iloc[-1]
    assert abs(metrics["ma150"] - expected_ma150) < 0.01


def test_compute_stock_metrics_short_series():
    """Test _compute_stock_metrics with short price series."""
    df = pd.DataFrame({
        "Close": [100, 101, 102, 103, 104],
        "Volume": [1000000] * 5,
    })

    metrics = _compute_stock_metrics(df, "TEST")

    # Should compute without error even with short series
    assert metrics["latest"] == 104
    assert "change_20d_pct" in metrics  # May be 0 if series too short


def test_compute_stock_metrics_with_multiindex_price_columns():
    dates = pd.date_range("2024-01-01", periods=80)
    df = pd.DataFrame(
        {
            ("Close", "TEST"): np.linspace(100, 120, 80),
            ("Volume", "TEST"): np.full(80, 1_000_000),
        },
        index=dates,
    )

    metrics = _compute_stock_metrics(df, "TEST")

    assert metrics["latest"] == 120
    assert "change_20d_pct" in metrics
    assert "volatility_20d" in metrics


def test_compute_stock_metrics_uses_densest_multiindex_series():
    dates = pd.date_range("2024-01-01", periods=80)
    df = pd.DataFrame(
        {
            ("Close", "AMBU"): [np.nan] * 80,
            ("Close", "B"): np.linspace(100, 120, 80),
            ("Volume", "AMBU"): [np.nan] * 80,
            ("Volume", "B"): [1_000_000] * 80,
        },
        index=dates,
    )

    metrics = _compute_stock_metrics(df, "AMBU B")

    assert metrics["latest"] == 120
    assert "change_20d_pct" in metrics


def test_compute_stock_metrics_with_mocked_yfinance(monkeypatch):
    """Test _compute_stock_metrics retrieves fundamental metrics from yfinance."""
    import yfinance as yf

    # Mock yfinance Ticker
    class MockTicker:
        def __init__(self, ticker):
            self.ticker = ticker
            self.info = {
                "trailingPE": 25.5,
                "dividendYield": 0.02,
                "priceToBook": 3.2,
                "returnOnEquity": 0.15,
                "debtToEquity": 0.8,
                "marketCap": 2.5e12,
            }
            self.quarterly_financials = pd.DataFrame()

    monkeypatch.setattr("sector_rotation.src.renderers.yf.Ticker", MockTicker)

    dates = pd.date_range("2024-01-01", periods=100)
    df = pd.DataFrame({
        "Close": np.linspace(100, 120, 100),
        "Volume": 1000000,
    }, index=dates)

    metrics = _compute_stock_metrics(df, "AAPL")

    # Verify fundamental metrics are present
    assert metrics["pe_ratio"] == 25.5
    assert metrics["dividend_yield"] == 0.02
    assert metrics["pb_ratio"] == 3.2
    assert metrics["roe"] == 0.15
    assert metrics["debt_to_equity"] == 0.8
    assert metrics["market_cap"] == 2.5e12


def test_render_data_card_calls_chart(monkeypatch):
    calls = []

    monkeypatch.setattr("sector_rotation.src.renderers.st.subheader", lambda title: calls.append(("subheader", title)))
    monkeypatch.setattr("sector_rotation.src.renderers.st.write", lambda *args, **kwargs: calls.append(("write", args)))
    monkeypatch.setattr("sector_rotation.src.renderers.render_chart", lambda *args, **kwargs: calls.append(("chart", args)))

    close = pd.Series([1, 2, 3, 4, 5])
    volume = pd.Series([10, 20, 30, 40, 50])

    render_data_card("My Title", close, volume, subtitle="sub", metadata="meta")

    assert ("subheader", "My Title") in calls
    assert any(call[0] == "chart" for call in calls)


def test_render_data_card_handles_dataframe_volume(monkeypatch):
    calls = []

    monkeypatch.setattr("sector_rotation.src.renderers.st.subheader", lambda title: calls.append(("subheader", title)))
    monkeypatch.setattr("sector_rotation.src.renderers.st.write", lambda *args, **kwargs: calls.append(("write", args)))
    monkeypatch.setattr("sector_rotation.src.renderers.render_chart", lambda *args, **kwargs: calls.append(("chart", args)))

    close = pd.Series([1, 2, 3, 4, 5])
    volume = pd.DataFrame({"A": [10, 20, 30, 40, 50], "B": [None, None, None, None, None]})

    render_data_card("My Title", close, volume, subtitle="sub", metadata="meta")

    assert ("subheader", "My Title") in calls
    assert any(call[0] == "chart" for call in calls)


def test_compute_return_vol_rr_outputs_expected_fields():
    close = pd.Series(np.linspace(100, 120, 80))

    metrics = _compute_return_vol_rr(close, lookback=30)

    assert "exp_return_ann_pct" in metrics
    assert "exp_vol_ann_pct" in metrics
    assert "risk_reward" in metrics
    assert isinstance(metrics["exp_vol_ann_pct"], float)


def test_news_topic_classifies_recent_headlines():
    assert _news_topic("Government signals new tariff plan") == "Politics"
    assert _news_topic("Inflation data points to cooling economy") == "Economy"
    assert _news_topic("Broker upgrade lifts target price") == "Rating"
    assert _news_topic("Company launches new product") == "General"


def test_get_trend_colors_handles_flat_series():
    colors = get_trend_colors(pd.Series([100.0] * 10))

    assert colors == ("#444444", "#cccccc")


def test_get_trend_colors_handles_dataframe_input():
    frame = pd.DataFrame({"A": [100.0] * 10, "B": [None] * 10})

    colors = get_trend_colors(frame)

    assert colors == ("#444444", "#cccccc")


def test_render_stock_details_panel_compact_mode_omits_scorecard_callout(monkeypatch):
    markdown_calls = []
    button_calls = []

    class _ContextStub:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_columns(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_ContextStub() for _ in range(count)]

    monkeypatch.setattr("sector_rotation.src.core.ui.view_components.st.session_state", {})
    monkeypatch.setattr("sector_rotation.src.core.ui.view_components.st.columns", fake_columns)
    monkeypatch.setattr("sector_rotation.src.core.ui.view_components.st.button", lambda label, **kwargs: button_calls.append(label) or False)
    monkeypatch.setattr("sector_rotation.src.core.ui.view_components.st.markdown", lambda text, **kwargs: markdown_calls.append(text))
    monkeypatch.setattr("sector_rotation.src.core.ui.view_components.st.caption", lambda *args, **kwargs: None)

    render_stock_details_panel(
        metrics={},
        company_name="Example Corp",
        ticker="EXM",
        universe="S&P 500",
        sector="Technology",
        industry="Software",
        show_liquidity_context=False,
        show_full_details=False,
        favorite_label="★",
        favorite_button_key="favorite-S&P 500-EXM",
        on_toggle=lambda *args, **kwargs: None,
        on_toggle_args=("S&P 500", "EXM"),
    )

    rendered_text = "\n".join(str(text) for text in markdown_calls)
    assert "Scorecard" not in rendered_text
    assert "Click to open full dedicated analysis" not in rendered_text
    assert "Example Corp" in rendered_text
    assert "EXM" in rendered_text
    assert "Technology" in rendered_text
    assert "Software" in rendered_text
    assert "★" in button_calls
