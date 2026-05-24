from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from .stock_focus import clear_dedicated_stock_view, pop_opening_ticker
from .view_config import BASE_CHART_WIDTH


DEDICATED_TOP_ROW_LAYOUT = [("chart", 1.2), ("details", 1.45)]
DEDICATED_CONTEXT_ROW_LAYOUT = [("macro", 1.0), ("recent", 1.0)]
DEDICATED_CHART_MIN_HEIGHT = 3.6
DEDICATED_CHART_WIDTH = BASE_CHART_WIDTH * 1.35


def dedicated_chart_size(chart_height: float) -> tuple[float, float]:
    return (DEDICATED_CHART_WIDTH, max(chart_height, DEDICATED_CHART_MIN_HEIGHT))


def render_dedicated_stock_view(
    selected_universe: str,
    focus_ticker: str,
    show_liquidity_context: bool,
    render_slot: Callable[[str], None],
) -> None:
    opening_ticker = pop_opening_ticker()
    if opening_ticker == focus_ticker:
        st.caption(f"Opening dedicated view for {focus_ticker}...")

    head_col, _spacer = st.columns([1, 7])
    with head_col:
        if st.button(
            "Back",
            key=f"details-focus-back-{selected_universe}",
            use_container_width=True,
        ):
            clear_dedicated_stock_view()
            st.rerun()
    st.caption(f"Dedicated stock view · {focus_ticker}")

    # Row 1: chart (left) | company header + hero stats (right)
    top_cols = st.columns([1.1, 1.0])
    with top_cols[0]:
        render_slot("chart")
    with top_cols[1]:
        render_slot("details_header")

    # Row 2–N: full-width scorecard criteria grid
    render_slot("details_body")

    # Row N+1: liquidity context + recent information
    if show_liquidity_context:
        ctx_cols = st.columns([1.0, 1.0])
        with ctx_cols[0]:
            render_slot("macro")
        with ctx_cols[1]:
            render_slot("recent")