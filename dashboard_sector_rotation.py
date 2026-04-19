import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import linregress

SECTORS = {
    "Technology": "XLK", "Healthcare": "XLV", "Financials": "XLF",
    "Consumer Disc": "XLY", "Consumer Staples": "XLP", "Energy": "XLE",
    "Industrials": "XLI", "Materials": "XLB", "Utilities": "XLU",
    "Real Estate": "XLRE", "Communication": "XLC"
}

def fetch_sector_data(ticker: str) -> pd.DataFrame:
    return yf.download(ticker, period="2y", progress=False)


def get_trend_colors(ma50: pd.Series) -> tuple[str, str]:
    recent_ma = ma50.dropna().tail(50)
    if len(recent_ma) <= 10:
        return "#444444", "#cccccc"

    x = range(len(recent_ma))
    slope = linregress(x, recent_ma).slope
    if slope < 0:
        return "#8b2020", "#ffaaaa"
    return "#1a6b1a", "#aaffaa"


def render_sector_chart(df: pd.DataFrame, close: pd.Series, ma50: pd.Series, bg_color: str, bar_color: str) -> None:
    fig, ax1 = plt.subplots(figsize=(5, 3))
    fig.patch.set_facecolor(bg_color)
    ax1.set_facecolor(bg_color)

    ax2 = ax1.twinx()
    volume = df['Volume'].squeeze()
    ax2.bar(volume.index, volume.values, color=bar_color, alpha=0.3, width=1.5)
    ax2.set_ylim(0, volume.max() * 2)
    ax2.set_ylabel("Volume", fontsize=7, color="lightgray")
    ax2.tick_params(axis='y', labelsize=6, colors="lightgray")
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v/1e6:.0f}M"))

    ax1.plot(close.index, close.values, color="#ffffff", linewidth=1.2, label="Price")
    ax1.plot(ma50.index, ma50.values, color="#ffdd44", linewidth=1.2, label="50 MA")
    ax1.set_ylabel("Price", fontsize=7, color="white")
    ax1.tick_params(axis='both', labelsize=6, colors="white")
    ax1.legend(fontsize=6, loc="upper left", facecolor="#333333", labelcolor="white")

    plt.tight_layout(pad=0.5)
    st.pyplot(fig)
    plt.close(fig)


def render_sector_card(name: str, ticker: str) -> None:
    df = fetch_sector_data(ticker)
    close = df['Close'].squeeze()
    ma50 = close.rolling(50).mean()
    bg_color, bar_color = get_trend_colors(ma50)

    st.subheader(f"{name} ({ticker})")
    render_sector_chart(df, close, ma50, bg_color, bar_color)


def main() -> None:
    st.set_page_config(page_title="Sector Rotation", layout="wide")
    st.title("Sector Rotation - 2 Year Overview")

    cols = st.columns(4)
    for i, (name, ticker) in enumerate(SECTORS.items()):
        with cols[i % 4]:
            render_sector_card(name, ticker)


if __name__ == "__main__":
    main()