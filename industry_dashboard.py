import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import linregress
import sys
import os

# Add the current directory to path to import industry_rotation functions
sys.path.append(os.path.dirname(__file__))
from industry_rotation import (
    normalize_sector_name, load_equities, fetch_sector_industries,
    fetch_industry_counts, INDUSTRY_ETFS
)


def fetch_industry_tickers(sector: str, industry: str, top_n: int = 20) -> list[str]:
    equities = load_equities()
    selected = equities.select(sector=sector, industry=industry, exclude_exchanges=False)
    # Sort by market cap descending and take top N
    if 'market_cap' in selected.columns:
        selected = selected.sort_values('market_cap', ascending=False)
    return selected.head(top_n).index.tolist()


def compute_industry_aggregate(tickers: list[str]) -> tuple[pd.Series, pd.Series]:
    if not tickers:
        return pd.Series(), pd.Series()

    # Download data for all tickers
    df = yf.download(tickers, period="2y", progress=False, group_by='ticker')

    if df.empty:
        return pd.Series(), pd.Series()

    # Compute average close and sum volume
    closes = []
    volumes = []
    for ticker in tickers:
        if ticker in df.columns.levels[0]:
            ticker_close = df[ticker]['Close']
            ticker_volume = df[ticker]['Volume']
            closes.append(ticker_close)
            volumes.append(ticker_volume)

    if not closes:
        return pd.Series(), pd.Series()

    # Align dates
    close_df = pd.concat(closes, axis=1, keys=tickers).ffill().dropna(axis=0, how='all')
    volume_df = pd.concat(volumes, axis=1, keys=tickers).fillna(0)

    # Compute equal-weighted index: average of pct_changes, then cumprod
    pct_changes = close_df.pct_change().mean(axis=1, skipna=True)
    index = (1 + pct_changes).cumprod() * 100  # Start at 100

    total_volume = volume_df.sum(axis=1)

    return index, total_volume

st.set_page_config(page_title="Industry Rotation", layout="wide")
st.title("Industry Rotation - 2 Year Overview")

# Sidebar for sector selection
equities = load_equities()
available_sectors = equities.options("sector")
sector_options = sorted(available_sectors.tolist()) + ["Custom Ticker"]
selected_option = st.sidebar.selectbox("Select Sector or Ticker", sector_options)

if selected_option == "Custom Ticker":
    custom_input = st.sidebar.text_input("Enter Sector Name or Ticker")
    if custom_input:
        try:
            sector = normalize_sector_name(custom_input, available_sectors)
        except ValueError as e:
            st.sidebar.error(str(e))
            st.stop()
    else:
        st.stop()
else:
    sector = selected_option

# Fetch data
industries = fetch_sector_industries(sector)
industry_counts = fetch_industry_counts(sector)

if industries.empty:
    st.write("No industries found for the given sector.")
else:
    st.write(f"**Sector:** {sector}")
    st.write(f"**Industries found:** {len(industries)}")

    cols = st.columns(3)  # Adjust columns as needed

    for i, industry in enumerate(industries):
        with cols[i % 3]:
            count = industry_counts.get(industry, 0)

            st.subheader(f"{industry}")
            st.write(f"{count} equities")

            # Get tickers and compute aggregate
            tickers = fetch_industry_tickers(sector, industry)
            if tickers:
                avg_close, total_volume = compute_industry_aggregate(tickers)
                if not avg_close.empty:
                    ma50 = avg_close.rolling(50).mean()

                    # Trend color logic
                    recent_ma = ma50.dropna().tail(10)
                    if len(recent_ma) > 10:
                        x = range(len(recent_ma))
                        slope = linregress(x, recent_ma).slope
                        bg_color = "#8b2020" if slope < 0 else "#1a6b1a"
                        bar_color = "#ffaaaa" if slope < 0 else "#aaffaa"
                    else:
                        bg_color = "#444444"
                        bar_color = "#cccccc"

                    # Plot
                    fig, ax1 = plt.subplots(figsize=(4, 2.5))
                    fig.patch.set_facecolor(bg_color)
                    ax1.set_facecolor(bg_color)

                    ax2 = ax1.twinx()
                    ax2.bar(total_volume.index, total_volume.values, color=bar_color, alpha=0.3, width=1.5)
                    ax2.set_ylim(0, total_volume.max() * 2)
                    ax2.set_ylabel("Volume", fontsize=6, color="lightgray")
                    ax2.tick_params(axis='y', labelsize=5, colors="lightgray")
                    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v/1e6:.0f}M"))

                    ax1.plot(avg_close.index, avg_close.values, color="#ffffff", linewidth=1, label="Index")
                    ax1.plot(ma50.index, ma50.values, color="#ffdd44", linewidth=1, label="50 MA")
                    ax1.set_ylabel("Price", fontsize=6, color="white")
                    ax1.tick_params(axis='both', labelsize=5, colors="white")
                    ax1.legend(fontsize=5, loc="upper left", facecolor="#333333", labelcolor="white")

                    plt.tight_layout(pad=0.3)
                    st.pyplot(fig)
                    plt.close(fig)
                else:
                    st.write("No data available for this industry.")
            else:
                st.write("No tickers found for this industry.")