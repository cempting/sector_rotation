import concurrent.futures
import streamlit as st
import pandas as pd
import yfinance as yf
from .charts import get_trend_colors, render_chart, render_stock_chart
from .constants import INDUSTRY_GRID_COLS, SECTOR_FIGSIZE, SECTOR_GRID_COLS
from .data import (
    compute_industry_aggregate,
    fetch_industry_counts,
    fetch_industry_tickers,
    fetch_sector_data,
    fetch_ticker_data_batch,
    get_db_sector_name,
    load_equities,
)
from .universe import get_universe_tickers, get_universe_industries


def safe_format(val):
    if hasattr(val, "item"):
        val = val.item()
    try:
        return f"{float(val):.2f}" if pd.notna(val) else "N/A"
    except (ValueError, TypeError):
        return "N/A"


def render_data_card(title: str, close: pd.Series, volume: pd.Series,
                      subtitle: str = "", metadata: str = "",
                      chart_params: dict = None, nav_action: callable = None) -> None:
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


def render_dashboard_grid(title: str, items: list, item_fetcher: callable,
                          cols: int = 3, back_nav: bool = False) -> None:
    st.title(title, )

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
    selected_universe = st.session_state.get("selected_universe", "S&P 500")
    industries = get_universe_industries(selected_universe, sector)

    if not industries:
        st.write("No industries found.")
        return

    columns = st.columns(INDUSTRY_GRID_COLS)
    for i, industry in enumerate(industries):
        with columns[i % INDUSTRY_GRID_COLS]:
            tickers = get_universe_tickers(selected_universe, sector=sector, industry=industry)
            count = len(tickers)

            if tickers:
                avg_close, total_volume, num_fetched = compute_industry_aggregate(tickers)
                render_data_card(
                    title=f"{industry} ({count})",
                    close=avg_close,
                    volume=total_volume,
                    chart_params={"y_label": "Index", "legend_label": "Index", "figsize": (4, 2.5)},
                    nav_action=lambda ind=industry: _nav_to_industry_stocks(sector, ind),
                )
            else:
                st.subheader(f"{industry} ({count})")
                st.caption("No data")


def _nav_to_industry_stocks(sector: str, industry: str) -> None:
    if st.button(f"View Stocks", key=f"stocks-{sector}-{industry}"):
        st.session_state.view = "industry_stocks"
        st.session_state.selected_sector = sector
        st.session_state.selected_industry = industry
        st.rerun()


def _compute_stock_metrics(df: pd.DataFrame, ticker: str) -> dict:
    """Compute key metrics for a stock including technicals and fundamentals."""
    metrics = {}
    
    # Technical metrics
    if not df.empty and "Close" in df.columns:
        close = df["Close"]
        latest = float(close.iloc[-1])
        prev_close = float(close.iloc[-20]) if len(close) > 20 else float(close.iloc[0])
        change_pct = ((latest - prev_close) / prev_close * 100) if prev_close > 0 else 0
        
        ma50 = float(close.rolling(50).mean().iloc[-1])
        ma150 = float(close.rolling(150).mean().iloc[-1])
        
        vol_20 = float(close.pct_change().tail(20).std() * 100) if len(close) > 20 else 0
        
        metrics.update({
            "latest": latest,
            "change_20d_pct": change_pct,
            "ma50": ma50,
            "ma150": ma150,
            "volatility_20d": vol_20,
        })
    
    # Fundamental metrics via yfinance
    try:
        tick = yf.Ticker(ticker)
        info = tick.info or {}
        
        metrics.update({
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "dividend_yield": info.get("dividendYield"),
            "pb_ratio": info.get("priceToBook"),
            "debt_to_equity": info.get("debtToEquity"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "eps_trailing": info.get("trailingEps"),
            "eps_forward": info.get("forwardEps"),
            "dividend_per_share": info.get("dividendRate"),
        })
        
        # Recent earnings dates
        try:
            earnings_dates = tick.quarterly_financials
            if not earnings_dates.empty:
                latest_earnings_date = earnings_dates.columns[0]
                metrics["latest_earnings_date"] = latest_earnings_date
        except:
            pass
            
    except Exception:
        pass
    
    return metrics


def _format_fundamental(val, is_pct=False):
    """Format fundamental metric values."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    try:
        val = float(val)
        if is_pct:
            return f"{val*100:.1f}%"
        elif val >= 1e9:
            return f"${val/1e9:.1f}B"
        elif val >= 1e6:
            return f"${val/1e6:.1f}M"
        else:
            return f"{val:.2f}"
    except (ValueError, TypeError):
        return "N/A"


def render_industry_stock_page(sector: str, industry: str) -> None:
    selected_universe = st.session_state.get("selected_universe", "S&P 500")
    all_tickers = get_universe_tickers(selected_universe, sector=sector, industry=industry)
    st.caption(f"{len(all_tickers)} stocks in {selected_universe}")

    # Load stock data once, then render a consolidated snapshot per card.
    with st.status(f"Loading all {len(all_tickers)} stocks...") as analysis_status:
        all_results: dict[str, pd.DataFrame] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_ticker = {
                executor.submit(fetch_ticker_data_batch, ticker, False): ticker for ticker in all_tickers
            }
            for i, future in enumerate(concurrent.futures.as_completed(future_to_ticker)):
                ticker, df = future.result()
                all_results[ticker] = df
                analysis_status.update(label=f"Loaded {i+1}/{len(all_tickers)} stocks...")
    
    # --- Individual Stock Charts (2 per row for larger display) ---
    st.subheader("Individual Stock Charts")
    
    stocks_per_page = st.number_input(
        "Stocks per page (multiple of 2)",
        min_value=2,
        max_value=100,
        value=10,
        step=2,
        key=f"stocks_per_page_{sector}_{industry}"
    )
    total_pages = (len(all_tickers) + stocks_per_page - 1) // stocks_per_page

    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            page = st.selectbox(
                "Page",
                options=list(range(1, total_pages + 1)),
                format_func=lambda x: f"Page {x} of {total_pages} ({len(all_tickers)} total stocks)",
                key=f"page_{sector}_{industry}"
            )
    else:
        page = 1

    start_idx = (page - 1) * stocks_per_page
    end_idx = min(start_idx + stocks_per_page, len(all_tickers))
    page_tickers = all_tickers[start_idx:end_idx]

    st.caption(f"Showing {start_idx + 1}-{end_idx} of {len(all_tickers)} stocks")

    # Display stocks in 2-column layout for larger charts
    for row_start in range(0, len(page_tickers), 2):
        row_tickers = page_tickers[row_start:row_start + 2]
        cols = st.columns(2)
        for col_idx, ticker in enumerate(row_tickers):
            df = all_results.get(ticker, pd.DataFrame())
            with cols[col_idx]:
                st.subheader(f"{ticker}")
                if df.empty or "Close" not in df.columns or "Volume" not in df.columns:
                    st.write("No data available for this stock.")
                    continue

                render_stock_chart(df, ticker)
                metrics = _compute_stock_metrics(df, ticker)
                if metrics:
                    st.caption("Snapshot")
                    snapshot_cols = st.columns(3)
                    with snapshot_cols[0]:
                        st.metric("Price", f"${metrics.get('latest', 0):.2f}", f"{metrics.get('change_20d_pct', 0):+.1f}%")
                        st.metric("P/E", _format_fundamental(metrics.get('pe_ratio')))
                        st.metric("ROE", _format_fundamental(metrics.get('roe'), is_pct=True))
                    with snapshot_cols[1]:
                        st.metric("Vol (20D)", f"{metrics.get('volatility_20d', 0):.1f}%")
                        st.metric("Div Yield", _format_fundamental(metrics.get('dividend_yield'), is_pct=True))
                        st.metric("Debt/Eq", _format_fundamental(metrics.get('debt_to_equity')))
                    with snapshot_cols[2]:
                        st.metric("Market Cap", _format_fundamental(metrics.get('market_cap')))
                        st.metric("EPS (TTM)", _format_fundamental(metrics.get('eps_trailing')))
                        st.metric("P/B", _format_fundamental(metrics.get('pb_ratio')))

    st.success(f"✓ Page {page} complete! Displayed {len(page_tickers)} stocks")


def render_sector_card(name: str, ticker: str) -> None:
    df = fetch_sector_data(ticker)
    close = df["Close"].squeeze() if not df.empty else pd.Series()
    volume = df["Volume"].squeeze() if not df.empty else pd.Series()

    def nav_to_industry() -> None:
        if st.button(f"View Industries", key=name):
            st.session_state.view = "industry"
            st.session_state.selected_sector = name
            st.session_state.pop("selected_industry", None)
            st.rerun()

    render_data_card(
        title=f"{name} ({ticker})",
        close=close,
        volume=volume,
        chart_params={"y_label": "Price", "legend_label": "Price", "figsize": SECTOR_FIGSIZE},
        nav_action=nav_to_industry,
    )
