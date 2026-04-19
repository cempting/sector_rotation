import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import linregress
from financedatabase import Equities

SECTORS = {
    "Technology": "XLK", "Healthcare": "XLV", "Financials": "XLF",
    "Consumer Disc": "XLY", "Consumer Staples": "XLP", "Energy": "XLE",
    "Industrials": "XLI", "Materials": "XLB", "Utilities": "XLU",
    "Real Estate": "XLRE", "Communication": "XLC"
}

def fetch_sector_data(ticker: str) -> pd.DataFrame:
    try:
        return yf.download(ticker, period="2y", progress=False)
    except Exception:
        return pd.DataFrame()


def get_trend_colors(ma_series: pd.Series, lookback: int = 50) -> tuple[str, str]:
    """Determine background and bar colors based on moving average trend."""
    recent_ma = ma_series.dropna().tail(lookback)
    if len(recent_ma) <= 10:
        return "#444444", "#cccccc"

    x = range(len(recent_ma))
    slope = linregress(x, recent_ma).slope
    if slope < 0:
        return "#8b2020", "#ffaaaa"
    return "#1a6b1a", "#aaffaa"


def render_volume_bars(ax: plt.Axes, volume: pd.Series, bar_color: str, fontsize: int = 7) -> None:
    """Render volume bars on secondary y-axis."""
    if volume.max() > 0:
        ax.bar(volume.index, volume.values, color=bar_color, alpha=0.3, width=1.5)
        ax.set_ylim(0, volume.max() * 2)
        ax.set_ylabel("Volume", fontsize=fontsize-1, color="lightgray")
        ax.tick_params(axis='y', labelsize=fontsize-1, colors="lightgray")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v/1e6:.0f}M"))


def render_chart(close: pd.Series, volume: pd.Series, ma_series: pd.Series, 
                 bg_color: str, bar_color: str, y_label: str = "Price",
                 legend_label: str = "Price", figsize: tuple = (5, 3)) -> None:
    """Generic chart rendering with price, moving average, and volume."""
    fig, ax1 = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(bg_color)
    ax1.set_facecolor(bg_color)

    # Volume on secondary axis
    ax2 = ax1.twinx()
    render_volume_bars(ax2, volume, bar_color, fontsize=7)

    # Price and moving average on primary axis
    fontsize = 7 if figsize[0] >= 5 else 6
    ax1.plot(close.index, close.values, color="#ffffff", linewidth=1.2, label=legend_label)
    ax1.plot(ma_series.index, ma_series.values, color="#ffdd44", linewidth=1.2, label="50 MA")
    ax1.set_ylabel(y_label, fontsize=fontsize, color="white")
    ax1.tick_params(axis='both', labelsize=fontsize-1, colors="white")
    ax1.legend(fontsize=fontsize-1, loc="upper left", facecolor="#333333", labelcolor="white")

    plt.tight_layout(pad=0.5)
    st.pyplot(fig)
    plt.close(fig)


def render_sector_chart(df: pd.DataFrame, close: pd.Series, ma50: pd.Series, bg_color: str, bar_color: str) -> None:
    """Render sector chart with price and volume."""
    volume = df['Volume'].squeeze()
    render_chart(close, volume, ma50, bg_color, bar_color, 
                 y_label="Price", legend_label="Price", figsize=(5, 3))


def load_equities() -> Equities:
    return Equities()


def fetch_sector_industries(sector: str) -> pd.Series:
    equities = load_equities()
    industries = equities.options("industry", sector=sector)
    return pd.Series(sorted(industries.tolist()), name="industry")


def fetch_industry_counts(sector: str) -> pd.Series:
    equities = load_equities()
    selected = equities.select(sector=sector, exclude_exchanges=False)
    return selected["industry"].dropna().value_counts().sort_values(ascending=False)


def fetch_industry_tickers(sector: str, industry: str) -> list[str]:
    equities = load_equities()
    selected = equities.select(sector=sector, industry=industry, exclude_exchanges=False)
    # Sort by market cap descending and return all available tickers
    if 'market_cap' in selected.columns:
        selected = selected.sort_values('market_cap', ascending=False)
    return selected.index.tolist()


def compute_industry_aggregate(tickers: list[str]) -> tuple[pd.Series, pd.Series, int]:
    if not tickers:
        return pd.Series(), pd.Series(), 0

    try:
        # Download data for all tickers
        df = yf.download(tickers, period="2y", progress=False, group_by='ticker')
    except Exception:
        return pd.Series(), pd.Series(), 0

    if df.empty:
        return pd.Series(), pd.Series(), 0

    # Compute average close and sum volume
    closes = []
    volumes = []
    for ticker in tickers:
        if ticker in df.columns.levels[0]:
            ticker_close = df[ticker]['Close']
            ticker_volume = df[ticker]['Volume']
            if not ticker_close.empty:
                closes.append(ticker_close)
                volumes.append(ticker_volume)

    num_fetched = len(closes)
    if num_fetched == 0:
        return pd.Series(), pd.Series(), 0

    # Align dates
    close_df = pd.concat(closes, axis=1, keys=tickers[:num_fetched]).ffill().dropna(axis=0, how='all')
    volume_df = pd.concat(volumes, axis=1, keys=tickers[:num_fetched]).fillna(0)

    # Compute equal-weighted index: average of pct_changes, then cumprod
    pct_changes = close_df.pct_change().mean(axis=1, skipna=True)
    index = (1 + pct_changes).cumprod() * 100  # Start at 100

    total_volume = volume_df.sum(axis=1)

    return index, total_volume, num_fetched


def render_data_card(title: str, close: pd.Series, volume: pd.Series, 
                      subtitle: str = "", metadata: str = "",
                      chart_params: dict = None, nav_action: callable = None) -> None:
    """Generic card renderer for sector or industry data."""
    st.subheader(title)
    if subtitle:
        st.write(subtitle)
    if metadata:
        st.write(metadata)
    
    if close.empty:
        st.write("No data available.")
        return
    
    ma50 = close.rolling(50).mean()
    bg_color, bar_color = get_trend_colors(ma50)
    
    params = chart_params or {"y_label": "Price", "legend_label": "Price", "figsize": (5, 3)}
    render_chart(close, volume, ma50, bg_color, bar_color, **params)
    
    if nav_action:
        nav_action()


def render_dashboard_grid(title: str, items: list[tuple], item_fetcher: callable,
                         cols: int = 3, back_nav: bool = False) -> None:
    """Generic grid renderer for multiple items (sectors or industries)."""
    st.title(title)
    
    if not items:
        st.write("No items found.")
        return
    
    columns = st.columns(cols)
    
    for i, item in enumerate(items):
        with columns[i % cols]:
            item_fetcher(item)
    
    if back_nav and st.button("Back"):
        st.session_state.view = "sector"
        st.rerun()


def render_industry_dashboard(sector: str) -> None:
    """Render dashboard of industries for a selected sector."""
    industries = fetch_sector_industries(sector)
    industry_counts = fetch_industry_counts(sector)
    
    def render_industry_item(industry: str) -> None:
        count = industry_counts.get(industry, 0)
        tickers = fetch_industry_tickers(sector, industry)
        
        if tickers:
            avg_close, total_volume, num_fetched = compute_industry_aggregate(tickers)
            metadata = f"({num_fetched} fetched)" if avg_close.empty else f"({num_fetched} fetched)"
            render_data_card(
                title=industry,
                close=avg_close,
                volume=total_volume,
                subtitle=f"{count} equities",
                metadata=metadata,
                chart_params={"y_label": "Index", "legend_label": "Index", "figsize": (4, 2.5)}
            )
        else:
            st.subheader(industry)
            st.write(f"{count} equities")
            st.write("No tickers found.")
    
    render_dashboard_grid(
        title=f"Industry Screener - {sector}",
        items=industries.tolist(),
        item_fetcher=render_industry_item,
        cols=3,
        back_nav=True
    )


def render_sector_card(name: str, ticker: str) -> None:
    """Render a single sector card with navigation."""
    df = fetch_sector_data(ticker)
    close = df['Close'].squeeze() if not df.empty else pd.Series()
    volume = df['Volume'].squeeze() if not df.empty else pd.Series()
    
    def nav_to_industry() -> None:
        if st.button(f"View Industries for {name}", key=name):
            st.session_state.view = "industry"
            st.session_state.selected_sector = name
            st.rerun()
    
    render_data_card(
        title=f"{name} ({ticker})",
        close=close,
        volume=volume,
        chart_params={"y_label": "Price", "legend_label": "Price", "figsize": (5, 3)},
        nav_action=nav_to_industry
    )


def main() -> None:
    st.set_page_config(page_title="Sector Screener", layout="wide")

    if "view" not in st.session_state:
        st.session_state.view = "sector"

    if st.session_state.view == "industry" and "selected_sector" in st.session_state:
        render_industry_dashboard(st.session_state.selected_sector)
    else:
        st.title("Sector Screener - 2 Year Overview")

        cols = st.columns(4)
        for i, (name, ticker) in enumerate(SECTORS.items()):
            with cols[i % 4]:
                render_sector_card(name, ticker)


if __name__ == "__main__":
    main()