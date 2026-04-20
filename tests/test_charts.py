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
