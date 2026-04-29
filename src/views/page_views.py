import streamlit as st
import pandas as pd
from collections.abc import Callable

from ..charts import get_trend_colors, render_chart
from ..constants import INDUSTRY_GRID_COLS, SECTOR_FIGSIZE
from ..logic.data_processing import compute_industry_aggregate
from ..data.data_retrieval import (
    fetch_sector_data,
    get_sector_industry_counts,
    get_universe_sector_stock_count,
    get_universe_tickers,
    search_all_universes,
)
from ..data.favorites import list_all_favorites
from .view_config import FAVORITES_CHART_HEIGHT, FAVORITES_ROW_LAYOUT


ComputeReturnVolFn = Callable[..., dict[str, float]]
RenderDataCardFn = Callable[..., None]
OpenIndustryStocksFn = Callable[[str, str], None]
RenderStockCardsFn = Callable[..., None]


def _render_stock_list_controls(
    *,
    sector: str,
    industry: str,
    title: str,
    count: int,
    tickers: list[str],
    open_industry_stocks: OpenIndustryStocksFn,
) -> None:
    btn_col, info_col = st.columns([4, 1])
    with btn_col:
        st.button(
            "View Stocks",
            key=f"stocks-{sector}-{industry}",
            on_click=open_industry_stocks,
            args=(sector, industry),
            use_container_width=True,
        )
    with info_col:
        with st.popover("ⓘ", use_container_width=True):
            st.markdown(f"**{title}**")
            st.caption(f"{count} stocks")
            for ticker in tickers:
                st.caption(ticker)


def render_industry_dashboard(
    sector: str,
    compute_return_vol_rr: ComputeReturnVolFn,
    render_data_card: RenderDataCardFn,
    open_industry_stocks: OpenIndustryStocksFn,
) -> None:
    selected_universe = st.session_state.get("selected_universe", "S&P 500")
    counts = get_sector_industry_counts(selected_universe, sector)
    industries = [ind for ind in counts if ind != "undefined"]
    undef_count = counts.get("undefined", 0)
    total = sum(counts.values())

    if not counts:
        st.write("No industries found.")
        return

    st.caption(
        f"**{total} stocks** total - {len(industries)} industries"
        + (f" · **{undef_count} unclassified**" if undef_count else "")
    )

    columns = st.columns(INDUSTRY_GRID_COLS)
    for i, industry in enumerate(industries):
        with columns[i % INDUSTRY_GRID_COLS]:
            tickers = get_universe_tickers(selected_universe, sector=sector, industry=industry)
            count = len(tickers)

            if tickers:
                with st.spinner(f"Building {industry} aggregate..."):
                    avg_close, total_volume, num_fetched = compute_industry_aggregate(tickers)
                risk_metrics = compute_return_vol_rr(avg_close, lookback=30)
                render_data_card(
                    title=f"{industry} ({count})",
                    close=avg_close,
                    volume=total_volume,
                    chart_params={"y_label": "Index", "legend_label": "Index", "figsize": (4, 2.5)},
                )
                st.caption(
                    f"Exp Vol (30D ann): {risk_metrics['exp_vol_ann_pct']:.1f}% · "
                    f"Risk/Reward: {risk_metrics['risk_reward']:+.2f}"
                )
            else:
                st.subheader(f"{industry} ({count})")
                st.caption("No data")

            _render_stock_list_controls(
                sector=sector,
                industry=industry,
                title=industry,
                count=count,
                tickers=tickers,
                open_industry_stocks=open_industry_stocks,
            )

    if undef_count:
        undef_tickers = get_universe_tickers(selected_universe, sector=sector, industry="undefined")
        col_idx = len(industries) % INDUSTRY_GRID_COLS
        with columns[col_idx]:
            st.subheader(f"Unclassified ({undef_count})")
            st.caption("No industry assigned")
            _render_stock_list_controls(
                sector=sector,
                industry="undefined",
                title="Unclassified",
                count=undef_count,
                tickers=undef_tickers,
                open_industry_stocks=open_industry_stocks,
            )


def render_industry_stock_page(
    sector: str,
    industry: str,
    render_stock_cards: RenderStockCardsFn,
) -> None:
    selected_universe = st.session_state.get("selected_universe", "S&P 500")
    all_tickers = get_universe_tickers(selected_universe, sector=sector, industry=industry)
    st.caption(f"{len(all_tickers)} stocks in {selected_universe}")
    render_stock_cards(
        tickers=all_tickers,
        selected_universe=selected_universe,
        empty_message="No stocks in this industry.",
    )
    st.success(f"✓ Complete! Displayed all {len(all_tickers)} stocks")


def render_favorites_page(render_stock_cards: RenderStockCardsFn) -> None:
    grouped = list_all_favorites()
    total = sum(len(tickers) for tickers in grouped.values())
    st.subheader("Favorites · All Universes")
    st.caption(f"{total} favorite stocks")

    if not grouped:
        st.info("No favorites yet. Open an industry stock page and tap ☆ Favorite.")
        return

    for universe_name, tickers in grouped.items():
        st.markdown(f"**{universe_name}**")
        render_stock_cards(
            tickers=tickers,
            selected_universe=universe_name,
            empty_message="",
            show_liquidity_context=True,
            stocks_per_row=1,
            chart_height=FAVORITES_CHART_HEIGHT,
            row_layout=FAVORITES_ROW_LAYOUT,
        )


def render_search_results_page(render_stock_cards: RenderStockCardsFn) -> None:
    query = st.session_state.get("search_query", "")
    matches = search_all_universes(query, per_universe_limit=12, total_limit=80)
    st.subheader("Search · All Universes")
    st.caption(f"Query: {query or '(empty)'}")
    st.caption(f"{len(matches)} matches")

    if not matches:
        st.info("No matching stocks found. Try ticker fragments or company name words.")
        return

    grouped: dict[str, list[str]] = {}
    for match in matches:
        grouped.setdefault(match["universe"], []).append(match["ticker"])

    for universe_name, tickers in grouped.items():
        st.markdown(f"**{universe_name}**")
        render_stock_cards(
            tickers=tickers,
            selected_universe=universe_name,
            empty_message="",
        )


def render_sector_industry_summary(universe: str, sector: str) -> None:
    counts = get_sector_industry_counts(universe, sector)
    total = sum(counts.values())
    undef_count = counts.get("undefined", 0)
    assigned = total - undef_count

    st.caption(f"**{total} stocks** · {assigned} classified · {undef_count} unclassified")

    if counts:
        rows = []
        for industry, cnt in counts.items():
            label = "_(unclassified)_" if industry == "undefined" else industry
            rows.append(f"- {label}: **{cnt}**")
        st.markdown("\n".join(rows))


def render_sector_card(name: str, ticker: str) -> None:
    def open_industry_view() -> None:
        st.session_state.view = "industry"
        st.session_state.selected_sector = name
        st.session_state.pop("selected_industry", None)

    with st.spinner(f"Loading {name}..."):
        df = fetch_sector_data(ticker)
    close = df["Close"].squeeze() if not df.empty else pd.Series()
    volume = df["Volume"].squeeze() if not df.empty else pd.Series()

    st.subheader(f"{name} ({ticker})")
    if close.empty:
        st.write("No data available.")
    else:
        ma50 = close.rolling(50).mean()
        bg_color, bar_color = get_trend_colors(ma50)
        render_chart(
            close,
            volume,
            ma50,
            bg_color,
            bar_color,
            y_label="Price",
            legend_label="Price",
            figsize=SECTOR_FIGSIZE,
        )

    btn_col, info_col = st.columns([4, 1])
    with btn_col:
        st.button("View Industries", key=name, on_click=open_industry_view, use_container_width=True)
    with info_col:
        universe = st.session_state.get("selected_universe", "S&P 500")
        counts = get_sector_industry_counts(universe, name)
        total = get_universe_sector_stock_count(universe, name)
        undef = counts.get("undefined", 0)
        with st.popover("ⓘ", use_container_width=True):
            st.markdown(f"**{name}**")
            st.caption(f"Total stocks: {total}")
            st.caption(f"Classified: {total - undef}")
            if undef:
                st.caption(f"Unclassified: {undef}")
            for industry, cnt in counts.items():
                label = "Unclassified" if industry == "undefined" else industry
                st.caption(f"{label}: {cnt}")
