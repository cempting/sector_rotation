"""Favorites feature rendering."""

import streamlit as st

from ...core.data import export_favorites_settings, import_favorites_settings, list_all_favorites
from ...core.ui import FAVORITES_CHART_HEIGHT, FAVORITES_ROW_LAYOUT, render_stock_cards


def render_favorites_page(render_stock_cards_fn=None) -> None:
    render_stock_cards_fn = render_stock_cards_fn or render_stock_cards

    grouped = list_all_favorites()
    total = sum(len(tickers) for tickers in grouped.values())
    st.subheader("Favorites · All Universes")
    st.caption(f"{total} favorite stocks")

    controls_left, controls_right = st.columns([1, 2])
    with controls_left:
        st.download_button(
            "Export favorites",
            data=export_favorites_settings(),
            file_name="favorites_settings.json",
            mime="application/json",
            use_container_width=True,
        )

    with controls_right:
        uploaded_file = st.file_uploader(
            "Import favorites settings",
            type=["json"],
            key="favorites_import_file",
        )
        merge_import = st.checkbox("Merge with existing favorites", value=True, key="favorites_import_merge")
        if uploaded_file is not None and st.button("Import favorites", key="favorites_import_apply"):
            try:
                universe_count, ticker_count = import_favorites_settings(uploaded_file.getvalue(), merge=merge_import)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success(f"Imported {ticker_count} favorites across {universe_count} universes.")
                st.rerun()

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
