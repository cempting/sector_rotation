"""Favorites feature rendering."""

import streamlit as st

from ...core.data import list_all_favorites
from ...core.ui import FAVORITES_CHART_HEIGHT, FAVORITES_ROW_LAYOUT, render_stock_cards


def render_favorites_page(render_stock_cards_fn=None) -> None:
    render_stock_cards_fn = render_stock_cards_fn or render_stock_cards

    grouped = list_all_favorites()
    total = sum(len(tickers) for tickers in grouped.values())
    st.subheader("Favorites · All Universes")
    st.caption(f"{total} favorite stocks")

    if not grouped:
        st.info("No favorites yet. Open an industry stock page and tap ☆ Favorite.")
        return

    for universe_name, tickers in grouped.items():
        st.markdown(f"**{universe_name}**")
        render_stock_cards_fn(
            tickers=tickers,
            selected_universe=universe_name,
            empty_message="",
            show_liquidity_context=True,
            stocks_per_row=1,
            chart_height=FAVORITES_CHART_HEIGHT,
            row_layout=FAVORITES_ROW_LAYOUT,
        )
