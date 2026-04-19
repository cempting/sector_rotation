import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import linregress
from financedatabase import Equities

# Constants
TREND_LOOKBACK_DAYS = 5
MIN_TREND_LENGTH = 4
TREND_SLOPE_THRESHOLD = 0
VOLUME_BAR_ALPHA = 0.3
VOLUME_BAR_WIDTH = 1.5
VOLUME_SCALE_FACTOR = 2
DEFAULT_FONTSIZE = 7
SECTOR_FIGSIZE = (5, 3)
INDUSTRY_FIGSIZE = (4, 2.5)
FIGSIZE_FONTSIZE_THRESHOLD = 5
SMALL_FONTSIZE = 6
LINE_WIDTH = 1.2
INDEX_START_VALUE = 100
DEFAULT_TOP_TICKERS = 150
SECTOR_GRID_COLS = 4
INDUSTRY_GRID_COLS = 3
TICKER_PERIOD="2y"

SECTORS = {
    "Technology": "XLK", 
    "Healthcare": "XLV", 
    "Financials": "XLF",
    "Consumer Disc": "XLY", 
    "Consumer Staples": "XLP", 
    "Energy": "XLE",
    "Industrials": "XLI", 
    "Materials": "XLB", 
    "Utilities": "XLU",
    "Real Estate": "XLRE", 
    "Communication": "XLC"
}

SECTOR_NAME_MAP = {
    "Technology": "Information Technology",
    "Healthcare": "Health Care",
    "Consumer Disc": "Consumer Discretionary",
    "Communication": "Communication Services"
}


def get_db_sector_name(sector: str) -> str:
    return SECTOR_NAME_MAP.get(sector, sector)


def fetch_sector_data(ticker: str) -> pd.DataFrame:
    try:
        return yf.download(ticker, period=TICKER_PERIOD, progress=False)
    except Exception:
        return pd.DataFrame()


def get_trend_colors(ma_series: pd.Series, lookback: int = TREND_LOOKBACK_DAYS) -> tuple[str, str]:
    """Determine background and bar colors based on moving average trend."""
    recent_ma = ma_series.dropna().tail(lookback)
    if len(recent_ma) <= MIN_TREND_LENGTH:
        return "#444444", "#cccccc"

    x = range(len(recent_ma))
    slope = linregress(x, recent_ma).slope
    if slope < TREND_SLOPE_THRESHOLD:
        return "#8b2020", "#ffaaaa"
    return "#1a6b1a", "#aaffaa"


def render_volume_bars(ax: plt.Axes, volume: pd.Series, bar_color: str, fontsize: int = DEFAULT_FONTSIZE) -> None:
    """Render volume bars on secondary y-axis."""
    if volume.max() > 0:
        ax.bar(volume.index, volume.values, color=bar_color, alpha=VOLUME_BAR_ALPHA, width=VOLUME_BAR_WIDTH)
        ax.set_ylim(0, volume.max() * VOLUME_SCALE_FACTOR)
        ax.set_ylabel("Volume", fontsize=fontsize-1, color="lightgray")
        ax.tick_params(axis='y', labelsize=fontsize-1, colors="lightgray")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v/1e6:.0f}M"))


def render_chart(close: pd.Series, volume: pd.Series, ma_series: pd.Series, 
                 bg_color: str, bar_color: str, y_label: str = "Price",
                 legend_label: str = "Price", figsize: tuple = SECTOR_FIGSIZE) -> None:
    """Generic chart rendering with price, moving average, and volume."""
    fig, ax1 = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(bg_color)
    ax1.set_facecolor(bg_color)

    # Volume on secondary axis
    ax2 = ax1.twinx()
    render_volume_bars(ax2, volume, bar_color, fontsize=DEFAULT_FONTSIZE)

    # Price and moving average on primary axis
    fontsize = DEFAULT_FONTSIZE if figsize[0] >= FIGSIZE_FONTSIZE_THRESHOLD else SMALL_FONTSIZE
    ax1.plot(close.index, close.values, color="#ffffff", linewidth=LINE_WIDTH, label=legend_label)
    ax1.plot(ma_series.index, ma_series.values, color="#ffdd44", linewidth=LINE_WIDTH, label="50 MA")
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
                 y_label="Price", legend_label="Price", figsize=SECTOR_FIGSIZE)


def load_equities() -> Equities:
    return Equities()


def fetch_sector_industries(sector: str) -> pd.Series:
    db_sector = get_db_sector_name(sector)
    equities = load_equities()
    industries = equities.options("industry", sector=db_sector)
    return pd.Series(sorted(industries.tolist()), name="industry")


def fetch_industry_counts(sector: str) -> pd.Series:
    db_sector = get_db_sector_name(sector)
    equities = load_equities()
    selected = equities.select(sector=db_sector, exclude_exchanges=False)
    return selected["industry"].dropna().value_counts().sort_values(ascending=False)


def validate_ticker(ticker: str) -> bool:
    """Check if a ticker is valid and available in yfinance."""
    try:
        info = yf.Ticker(ticker).info
        return bool(info and 'symbol' in info)
    except Exception:
        return False


def fetch_industry_tickers(sector: str, industry: str, top_n: int = DEFAULT_TOP_TICKERS) -> list[str]:
    db_sector = get_db_sector_name(sector)
    equities = load_equities()
    selected = equities.select(sector=db_sector, industry=industry, exclude_exchanges=False)
    
    # Sort by market cap descending
    if 'market_cap' in selected.columns:
        selected = selected.sort_values('market_cap', ascending=False)
    
    # Validate tickers and collect valid ones
    valid_tickers = []
    for ticker in selected.index:
        if validate_ticker(ticker):
            valid_tickers.append(ticker)
            if len(valid_tickers) >= top_n:
                break
        # Continue checking until we have enough valid tickers
    
    return valid_tickers


def compute_industry_aggregate(tickers: list[str]) -> tuple[pd.Series, pd.Series, int]:
    if not tickers:
        return pd.Series(), pd.Series(), 0

    # Fetch tickers sequentially, skipping failed downloads
    closes = []
    volumes = []
    
    for ticker in tickers:
        try:
            # Download data for this single ticker
            df = yf.download(ticker, period="2y", progress=False)
            if not df.empty and 'Close' in df.columns and 'Volume' in df.columns:
                ticker_close = df['Close']
                ticker_volume = df['Volume']
                if not ticker_close.empty:
                    closes.append(ticker_close)
                    volumes.append(ticker_volume)
        except Exception:
            # Skip this ticker and continue with the next one
            continue
    
    num_fetched = len(closes)
    if num_fetched == 0:
        return pd.Series(), pd.Series(), 0

    # Align dates
    close_df = pd.concat(closes, axis=1, keys=[f"ticker_{i}" for i in range(num_fetched)]).ffill().dropna(axis=0, how='all')
    volume_df = pd.concat(volumes, axis=1, keys=[f"ticker_{i}" for i in range(num_fetched)]).fillna(0)

    # Compute equal-weighted index: average of pct_changes, then cumprod
    pct_changes = close_df.pct_change().mean(axis=1, skipna=True)
    index = (1 + pct_changes).cumprod() * INDEX_START_VALUE  # Start at 100

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
    industry_counts = fetch_industry_counts(sector)
    industries = industry_counts.index.tolist()
    
    def render_industry_item(industry: str) -> None:
        count = industry_counts.get(industry, 0)
        tickers = fetch_industry_tickers(sector, industry)
        
        if tickers:
            avg_close, total_volume, num_fetched = compute_industry_aggregate(tickers)
            metadata = f"({num_fetched} fetched)"
            render_data_card(
                title=industry + f" ({num_fetched}/{count})",
                close=avg_close,
                volume=total_volume,
                chart_params={"y_label": "Index", "legend_label": "Index", "figsize": INDUSTRY_FIGSIZE}
            )
        else:
            st.subheader(industry)
            st.write(f"{count} equities")
            st.write("No tickers found.")
    
    render_dashboard_grid(
        title=f"Industry Screener - {sector}",
        items=industries,
        item_fetcher=render_industry_item,
        cols=INDUSTRY_GRID_COLS,
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
        chart_params={"y_label": "Price", "legend_label": "Price", "figsize": SECTOR_FIGSIZE},
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

        cols = st.columns(SECTOR_GRID_COLS)
        for i, (name, ticker) in enumerate(SECTORS.items()):
            with cols[i % 4]:
                render_sector_card(name, ticker)


if __name__ == "__main__":
    main()