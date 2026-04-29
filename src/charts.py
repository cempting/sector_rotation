import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import linregress
from .constants import (
    DEFAULT_FONTSIZE,
    FIGSIZE_FONTSIZE_THRESHOLD,
    LINE_WIDTH,
    MIN_TREND_LENGTH,
    SECTOR_FIGSIZE,
    SMALL_FONTSIZE,
    TREND_LOOKBACK_DAYS,
    TREND_SLOPE_THRESHOLD,
    VOLUME_BAR_ALPHA,
    VOLUME_BAR_WIDTH,
    VOLUME_SCALE_FACTOR,
)


def get_trend_colors(ma_series: pd.Series, lookback: int = TREND_LOOKBACK_DAYS) -> tuple[str, str]:
    recent_ma = ma_series.dropna().tail(lookback)
    if len(recent_ma) <= MIN_TREND_LENGTH:
        return "#444444", "#cccccc"

    x = range(len(recent_ma))
    slope = linregress(x, recent_ma).slope
    if slope < TREND_SLOPE_THRESHOLD:
        return "#8b2020", "#ffaaaa"
    return "#1a6b1a", "#aaffaa"


def render_volume_bars(ax: plt.Axes, volume: pd.Series, bar_color: str, fontsize: int = DEFAULT_FONTSIZE) -> None:
    if volume.max() > 0:
        ax.bar(volume.index, volume.values, color=bar_color, alpha=VOLUME_BAR_ALPHA, width=VOLUME_BAR_WIDTH)
        ax.set_ylim(0, volume.max() * VOLUME_SCALE_FACTOR)
        ax.set_ylabel("Volume", fontsize=fontsize - 1, color="lightgray")
        ax.tick_params(axis='y', labelsize=fontsize - 1, colors="lightgray")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v/1e6:.0f}M"))


def render_chart(close: pd.Series, volume: pd.Series, ma_series: pd.Series,
                 bg_color: str, bar_color: str, y_label: str = "Price",
                 legend_label: str = "Price", figsize: tuple = SECTOR_FIGSIZE) -> None:
    fig, ax1 = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(bg_color)
    ax1.set_facecolor(bg_color)

    ax2 = ax1.twinx()
    render_volume_bars(ax2, volume, bar_color, fontsize=DEFAULT_FONTSIZE)

    fontsize = DEFAULT_FONTSIZE if figsize[0] >= FIGSIZE_FONTSIZE_THRESHOLD else SMALL_FONTSIZE
    ax1.plot(close.index, close.values, color="#ffffff", linewidth=LINE_WIDTH, label=legend_label)
    ax1.plot(ma_series.index, ma_series.values, color="#ffdd44", linewidth=LINE_WIDTH, label="50 MA")
    ax1.set_ylabel(y_label, fontsize=fontsize, color="white")
    ax1.tick_params(axis='both', labelsize=fontsize - 1, colors="white")
    ax1.legend(fontsize=fontsize - 1, loc="upper left", facecolor="#333333", labelcolor="white")

    plt.tight_layout(pad=0.5)
    st.pyplot(fig)
    plt.close(fig)


def render_sector_chart(df: pd.DataFrame, close: pd.Series, ma50: pd.Series, bg_color: str, bar_color: str) -> None:
    volume = df['Volume'].squeeze()
    render_chart(close, volume, ma50, bg_color, bar_color,
                 y_label="Price", legend_label="Price", figsize=SECTOR_FIGSIZE)


def _coerce_numeric_series(values: pd.Series | pd.DataFrame, ticker: str) -> pd.Series:
    if isinstance(values, pd.Series):
        return pd.to_numeric(values, errors='coerce').dropna()

    if isinstance(values, pd.DataFrame):
        if values.empty:
            return pd.Series(dtype=float)

        numeric = values.apply(pd.to_numeric, errors='coerce')
        if numeric.empty:
            return pd.Series(dtype=float)

        non_null_counts = numeric.notna().sum(axis=0)
        if non_null_counts.empty or int(non_null_counts.max()) == 0:
            return pd.Series(dtype=float)

        if ticker in numeric.columns:
            selected = numeric[ticker]
        else:
            selected = numeric.loc[:, non_null_counts.idxmax()]
        return selected.dropna()

    return pd.Series(dtype=float)


def render_stock_chart(df: pd.DataFrame, ticker: str, figsize: tuple[float, float] = (8, 5.8)) -> None:
    close = _coerce_numeric_series(df['Close'], ticker)
    volume = _coerce_numeric_series(df['Volume'], ticker)
    if close.empty or volume.empty:
        st.write(f"{ticker} could not be charted")
        return

    volume = volume.reindex(close.index).fillna(0)
    ma50 = close.rolling(50).mean()
    ma150 = close.rolling(150).mean()
    bg_color, bar_color = get_trend_colors(ma50)

    fig, ax1 = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(bg_color)
    ax1.set_facecolor(bg_color)

    ax2 = ax1.twinx()
    render_volume_bars(ax2, volume, bar_color, fontsize=DEFAULT_FONTSIZE)

    fontsize = DEFAULT_FONTSIZE
    ax1.plot(close.index, close.values, color="#ffffff", linewidth=LINE_WIDTH, label="Price")
    ax1.plot(ma50.index, ma50.values, color="#ffdd44", linewidth=LINE_WIDTH, label="50 MA")
    ax1.plot(ma150.index, ma150.values, color="#00aaff", linewidth=LINE_WIDTH, label="150 MA")
    ax1.set_ylabel("Price", fontsize=fontsize, color="white")
    ax1.tick_params(axis='both', labelsize=fontsize - 1, colors="white")
    ax1.legend(fontsize=fontsize - 1, loc="upper left", facecolor="#333333", labelcolor="white")

    plt.tight_layout(pad=0.5)
    st.pyplot(fig)
    plt.close(fig)
