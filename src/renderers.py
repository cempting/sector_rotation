import concurrent.futures
import streamlit as st
import pandas as pd
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

    def render_industry_item(industry: str) -> None:
        tickers = get_universe_tickers(selected_universe, sector=sector, industry=industry)
        count = len(tickers)

        def nav_to_stock_list() -> None:
            if st.button(f"View Stocks", key=f"stocks-{sector}-{industry}"):
                st.session_state.view = "industry_stocks"
                st.session_state.selected_sector = sector
                st.session_state.selected_industry = industry
                st.rerun()

        if tickers:
            avg_close, total_volume, num_fetched = compute_industry_aggregate(tickers)
            metadata = f"({num_fetched}/{count} in universe)"
            render_data_card(
                title=industry,
                close=avg_close,
                volume=total_volume,
                subtitle=f"{count} equities",
                metadata=metadata,
                chart_params={"y_label": "Index", "legend_label": "Index", "figsize": (4, 2.5)},
                nav_action=nav_to_stock_list,
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
        back_nav=True,
    )


def render_industry_stock_page(sector: str, industry: str) -> None:
    st.title(f"{industry} Stocks - {sector}")

    if st.button("Back to Industries"):
        st.session_state.view = "industry"
        st.rerun()

    selected_universe = st.session_state.get("selected_universe", "S&P 500")
    all_tickers = get_universe_tickers(selected_universe, sector=sector, industry=industry)
    st.write(f"Showing {len(all_tickers)} stocks in {selected_universe}.")

    stocks_per_page = st.number_input(
        "Stocks per page (multiple of 4)",
        min_value=4,
        max_value=100,
        value=20,
        step=4,
        key=f"stocks_per_page_{sector}_{industry}"
    )
    total_pages = (len(all_tickers) + stocks_per_page - 1) // stocks_per_page

    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            page = st.selectbox(
                "Page",
                options=list(range(1, total_pages + 1)),
                format_func=lambda x: f"Page {x} of {total_pages} ({len(all_tickers)} total candidates)",
                key=f"page_{sector}_{industry}"
            )
    else:
        page = 1

    start_idx = (page - 1) * stocks_per_page
    end_idx = min(start_idx + stocks_per_page, len(all_tickers))
    page_tickers = all_tickers[start_idx:end_idx]

    st.write(f"Showing tickers {start_idx + 1}-{end_idx} of {len(all_tickers)} candidates")

    # Add refresh button and status
    refresh_key = f"refresh_{sector}_{industry}_page_{page}"
    force_refresh = st.button("Refresh Data for This Page", key=refresh_key)
    if force_refresh:
        st.info("Forcing yfinance refresh for all tickers on this page...")
    else:
        st.caption("Using cached data where available. Click refresh to update from yfinance.")

    if page_tickers:
        page_results: dict[str, pd.DataFrame] = {}
        with st.status(f"Loading page {page}...") as status_container:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_ticker = {
                    executor.submit(fetch_ticker_data_batch, ticker, force_refresh): ticker for ticker in page_tickers
                }
                for i, future in enumerate(concurrent.futures.as_completed(future_to_ticker)):
                    ticker, df = future.result()
                    page_results[ticker] = df
                    status_container.update(label=f"Loaded {i+1}/{len(page_tickers)} tickers for page {page}...")

        st.write("### Stock charts")
        for row_start in range(0, len(page_tickers), 4):
            row_tickers = page_tickers[row_start:row_start + 4]
            cols = st.columns(4)
            for col_idx, ticker in enumerate(row_tickers):
                df = page_results.get(ticker, pd.DataFrame())
                with cols[col_idx]:
                    st.subheader(f"{ticker}")
                    if df.empty or "Close" not in df.columns or "Volume" not in df.columns:
                        st.write("No data available for this stock.")
                        continue

                    render_stock_chart(df, ticker)
                    latest_price = df["Close"].iloc[-1]
                    ma50 = df["Close"].rolling(50).mean().iloc[-1]
                    ma150 = df["Close"].rolling(150).mean().iloc[-1]
                    st.write(f"Latest: {safe_format(latest_price)} | 50MA: {safe_format(ma50)} | 150MA: {safe_format(ma150)}")

        st.success(f"✓ Page {page} complete! Loaded {len(page_tickers)} stocks")


def render_sector_card(name: str, ticker: str) -> None:
    df = fetch_sector_data(ticker)
    close = df["Close"].squeeze() if not df.empty else pd.Series()
    volume = df["Volume"].squeeze() if not df.empty else pd.Series()

    def nav_to_industry() -> None:
        if st.button(f"View Industries for {name}", key=name):
            st.session_state.view = "industry"
            st.session_state.selected_sector = name
            # Do NOT set sidebar_selected_sector here to avoid StreamlitAPIException
            st.rerun()

    render_data_card(
        title=f"{name} ({ticker})",
        close=close,
        volume=volume,
        chart_params={"y_label": "Price", "legend_label": "Price", "figsize": SECTOR_FIGSIZE},
        nav_action=nav_to_industry,
    )
