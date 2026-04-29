import streamlit as st
from collections.abc import Callable

from ..charts import render_stock_chart
from ..data.data_retrieval import fetch_ticker_data_batch, get_universe_stock_name
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

    for row_start in range(0, len(tickers), stocks_per_row):
        row_tickers = tickers[row_start:row_start + stocks_per_row]
        cols = st.columns(stocks_per_row)
        for col_idx, ticker in enumerate(row_tickers):
            with cols[col_idx]:
                with st.spinner(f"Loading {ticker}..."):
                    _, df = fetch_ticker_data_batch(ticker, False)
                if df.empty or "Close" not in df.columns or "Volume" not in df.columns:
                    st.write(f"{ticker} could not be loaded")
                    continue

                metrics = compute_stock_metrics(df, ticker)
                company_name = get_universe_stock_name(selected_universe, ticker)
                classification = stock_classification(selected_universe, ticker)

                macro = macro_impact_snapshot(ticker) if show_liquidity_context else {}
                recent = recent_info_snapshot(selected_universe, ticker) if show_liquidity_context else {}

                columns = st.columns([width for _, width in active_layout])
                for (slot, _), slot_col in zip(active_layout, columns):
                    with slot_col:
                        if slot == "chart":
                            chart_size = (
                                (BASE_CHART_WIDTH, liquidity_chart_height)
                                if show_liquidity_context
                                else DEFAULT_STOCK_CHART_SIZE
                            )
                            render_stock_chart(df, ticker, figsize=chart_size)
                            continue

                        if not metrics:
                            if slot == "details":
                                st.caption("No snapshot metrics available.")
                            elif slot == "macro":
                                st.caption("No liquidity context available.")
                            elif slot == "recent":
                                st.caption("No recent information available.")
                            continue

                        if slot == "details":
                            render_stock_details_panel(
                                metrics,
                                company_name,
                                ticker,
                                selected_universe,
                                sector=classification.get("sector", "N/A"),
                                industry=classification.get("industry", "N/A"),
                                show_liquidity_context=show_liquidity_context,
                            )
                        elif slot == "macro":
                            render_macro_context_card(metrics, macro, recent=recent)
                        elif slot == "recent":
                            render_recent_information_card(recent)
