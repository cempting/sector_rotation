import streamlit as st
import pandas as pd
from collections.abc import Callable

from ...charts import render_stock_chart
from ...core.data.data_retrieval import fetch_market_data_with_status, get_universe_stock_name
from .dedicated_stock_view import dedicated_chart_size, render_dedicated_stock_view
from .stock_focus import is_dedicated_focus_for_ticker
from .view_config import (
    BASE_CHART_WIDTH,
    DEFAULT_STOCK_CHART_SIZE,
    LIQUIDITY_STOCK_CHART_DEFAULT_HEIGHT,
    normalize_row_layout,
)


ComputeStockMetricsFn = Callable[..., dict]
StockClassificationFn = Callable[[str, str], dict[str, str]]
MacroImpactSnapshotFn = Callable[[str], dict[str, str | float]]
RecentInfoSnapshotFn = Callable[[str, str], dict[str, object]]
RenderStockDetailsPanelFn = Callable[..., None]
RenderMacroContextCardFn = Callable[..., None]
RenderRecentInformationCardFn = Callable[[dict[str, object]], None]


def render_stock_cards(
    tickers: list[str],
    selected_universe: str,
    empty_message: str,
    show_liquidity_context: bool,
    stocks_per_row: int,
    chart_height: float | None,
    row_layout: list[tuple[str, float]] | None,
    compute_stock_metrics: ComputeStockMetricsFn,
    stock_classification: StockClassificationFn,
    macro_impact_snapshot: MacroImpactSnapshotFn,
    recent_info_snapshot: RecentInfoSnapshotFn,
    render_stock_details_panel: RenderStockDetailsPanelFn,
    render_macro_context_card: RenderMacroContextCardFn,
    render_recent_information_card: RenderRecentInformationCardFn,
) -> None:
    # The card layout and chart sizing are config-driven by view_config.
    if not tickers:
        st.info(empty_message)
        return

    active_layout = normalize_row_layout(row_layout, show_liquidity_context)
    liquidity_chart_height = chart_height if chart_height is not None else LIQUIDITY_STOCK_CHART_DEFAULT_HEIGHT

    focus_ticker = is_dedicated_focus_for_ticker(selected_universe, tickers)
    focus_mode = bool(focus_ticker)
    render_tickers = [focus_ticker] if focus_mode else tickers

    for row_start in range(0, len(render_tickers), stocks_per_row):
        row_tickers = render_tickers[row_start:row_start + stocks_per_row]
        cols = st.columns(stocks_per_row)
        for col_idx, ticker in enumerate(row_tickers):
            with cols[col_idx]:
                with st.spinner(f"Loading {ticker}..."):
                    data_map, status_map = fetch_market_data_with_status(
                        [ticker],
                        force_refresh=False,
                        use_cache=True,
                        allow_stale_cache_fallback=True,
                    )
                    df = data_map.get(ticker, pd.DataFrame())
                    data_status = status_map.get(ticker, {})
                status_label = str(data_status.get("label", "No data"))
                st.caption(f"Data freshness: {status_label}")
                if df.empty or "Close" not in df.columns or "Volume" not in df.columns:
                    st.write(f"{ticker} could not be loaded")
                    continue

                metrics = compute_stock_metrics(df, ticker)
                company_name = get_universe_stock_name(selected_universe, ticker)
                classification = stock_classification(selected_universe, ticker)

                macro = macro_impact_snapshot(ticker) if show_liquidity_context else {}
                recent = recent_info_snapshot(selected_universe, ticker) if show_liquidity_context else {}

                def render_slot(slot: str) -> None:
                    if slot == "chart":
                        chart_size = (
                            dedicated_chart_size(liquidity_chart_height)
                            if focus_mode
                            else (
                                (BASE_CHART_WIDTH, liquidity_chart_height)
                                if show_liquidity_context
                                else DEFAULT_STOCK_CHART_SIZE
                            )
                        )
                        render_stock_chart(df, ticker, figsize=chart_size)
                        return

                    if not metrics:
                        if slot == "details":
                            st.caption("No snapshot metrics available.")
                        elif slot == "macro":
                            st.caption("No liquidity context available.")
                        elif slot == "recent":
                            st.caption("No recent information available.")
                        return

                    if slot == "details":
                        render_stock_details_panel(
                            metrics,
                            company_name,
                            ticker,
                            selected_universe,
                            sector=classification.get("sector", "N/A"),
                            industry=classification.get("industry", "N/A"),
                            show_liquidity_context=show_liquidity_context,
                            show_full_details=focus_mode,
                        )
                    elif slot == "details_header":
                        render_stock_details_panel(
                            metrics,
                            company_name,
                            ticker,
                            selected_universe,
                            sector=classification.get("sector", "N/A"),
                            industry=classification.get("industry", "N/A"),
                            show_liquidity_context=show_liquidity_context,
                            show_full_details=focus_mode,
                            detail_section="header",
                        )
                    elif slot == "details_body":
                        render_stock_details_panel(
                            metrics,
                            company_name,
                            ticker,
                            selected_universe,
                            sector=classification.get("sector", "N/A"),
                            industry=classification.get("industry", "N/A"),
                            show_liquidity_context=show_liquidity_context,
                            show_full_details=focus_mode,
                            detail_section="body",
                        )
                    elif slot == "macro":
                        render_macro_context_card(metrics, macro, recent=recent)
                    elif slot == "recent":
                        render_recent_information_card(recent)

                if focus_mode:
                    render_dedicated_stock_view(
                        selected_universe=selected_universe,
                        focus_ticker=ticker,
                        show_liquidity_context=show_liquidity_context,
                        render_slot=render_slot,
                    )
                    continue

                columns = st.columns([width for _, width in active_layout])
                for (slot, _), slot_col in zip(active_layout, columns):
                    with slot_col:
                        render_slot(slot)
