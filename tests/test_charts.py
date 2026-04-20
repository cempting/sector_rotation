import pandas as pd

from sector_rotation.src.charts import get_trend_colors, render_chart, render_stock_chart


def test_get_trend_colors_uptrend():
    series = pd.Series([1, 2, 3, 4, 5, 6])
    bg, bar = get_trend_colors(series, lookback=5)
    assert bg == "#1a6b1a"
    assert bar == "#aaffaa"


def test_get_trend_colors_downtrend():
    series = pd.Series([6, 5, 4, 3, 2, 1])
    bg, bar = get_trend_colors(series, lookback=5)
    assert bg == "#8b2020"
    assert bar == "#ffaaaa"


def test_render_chart(monkeypatch):
    recorded = []
    monkeypatch.setattr("sector_rotation.src.charts.st.pyplot", lambda fig: recorded.append(fig))

    close = pd.Series([10, 11, 12, 13, 14, 15], index=pd.date_range("2020-01-01", periods=6))
    volume = pd.Series([100, 110, 120, 130, 140, 150], index=close.index)
    ma = close.rolling(2).mean()

    render_chart(close, volume, ma, bg_color="#000000", bar_color="#00ff00", figsize=(4, 2))
    assert len(recorded) == 1


def test_render_stock_chart(monkeypatch):
    recorded = []
    monkeypatch.setattr("sector_rotation.src.charts.st.pyplot", lambda fig: recorded.append(fig))

    df = pd.DataFrame(
        {"Close": [10, 11, 12, 13, 14, 15], "Volume": [100, 110, 120, 130, 140, 150]},
        index=pd.date_range("2020-01-01", periods=6),
    )

    render_stock_chart(df, "AAPL")
    assert len(recorded) == 1


def test_render_stock_chart_uses_taller_figure(monkeypatch):
    recorded = []
    monkeypatch.setattr("sector_rotation.src.charts.st.pyplot", lambda fig: recorded.append(fig))

    df = pd.DataFrame(
        {
            "Close": [10, 11, 12, 13, 14, 15, 16, 17],
            "Volume": [100, 110, 120, 130, 140, 150, 160, 170],
        },
        index=pd.date_range("2020-01-01", periods=8),
    )

    render_stock_chart(df, "MSFT")

    assert len(recorded) == 1
    width, height = recorded[0].get_size_inches()
    assert width == 8
    assert height == 4


def test_render_stock_chart_plots_price_and_mas(monkeypatch):
    recorded = []
    monkeypatch.setattr("sector_rotation.src.charts.st.pyplot", lambda fig: recorded.append(fig))

    df = pd.DataFrame(
        {
            "Close": list(range(1, 201)),
            "Volume": [1000] * 200,
        },
        index=pd.date_range("2020-01-01", periods=200),
    )

    render_stock_chart(df, "NVDA")

    assert len(recorded) == 1
    # ax1 contains Price, 50 MA, and 150 MA lines.
    ax1 = recorded[0].axes[0]
    assert len(ax1.lines) == 3
