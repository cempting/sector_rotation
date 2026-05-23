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

    top_columns = st.columns([width for _, width in DEDICATED_TOP_ROW_LAYOUT])
    for (slot, _), slot_col in zip(DEDICATED_TOP_ROW_LAYOUT, top_columns):
        with slot_col:
            render_slot(slot)

    if show_liquidity_context:
        context_columns = st.columns([width for _, width in DEDICATED_CONTEXT_ROW_LAYOUT])
        for (slot, _), slot_col in zip(DEDICATED_CONTEXT_ROW_LAYOUT, context_columns):
            with slot_col:
                render_slot(slot)