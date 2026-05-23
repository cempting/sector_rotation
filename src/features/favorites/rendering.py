"""Favorites feature rendering."""

import streamlit as st

from ...core.data import list_all_favorites
from ...core.ui import FAVORITES_CHART_HEIGHT, FAVORITES_ROW_LAYOUT, render_grouped_stock_sections, render_stock_cards


FAVORITES_COMPACT_ROW_LAYOUT = [
    ("chart", 1.2),
    ("details", 1.0),
    ("macro", 0.9),
]
FAVORITES_COMPACT_CHART_HEIGHT = 2.2


def render_favorites_page(
    render_stock_cards_fn=None,
) -> None:
    render_stock_cards_fn = render_stock_cards_fn or render_stock_cards

    grouped = list_all_favorites()
    total = sum(len(tickers) for tickers in grouped.values())
    st.markdown(
        """
        <style>
        .favorites-view .sr-workbench {
            padding: 0.3rem 0.34rem;
            border-radius: 0.58rem;
        }
        .favorites-view .sr-hero {
            margin-bottom: 0.2rem;
            padding: 0.24rem 0.28rem;
        }
        .favorites-view .sr-hero-grid {
            gap: 0.14rem;
        }
        .favorites-view .sr-pane {
            margin-bottom: 0.16rem;
            padding: 0.22rem 0.24rem;
        }
        .favorites-view .sr-details-card {
            margin-bottom: 0.12rem;
            min-height: 1.78rem;
            padding: 0.16rem 0.24rem;
        }
        .favorites-view .sr-details-value {
            font-size: 0.9rem;
        }
        .favorites-view .sr-details-explain {
            font-size: 0.52rem;
            line-height: 1.08;
        }
        .favorites-view .favorites-open-primary button {
            border: 1px solid rgba(78, 203, 113, 0.55) !important;
            background: linear-gradient(180deg, rgba(78,203,113,0.22), rgba(78,203,113,0.1)) !important;
            font-weight: 650 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="favorites-view">', unsafe_allow_html=True)
    st.subheader("Favorites · All Universes")
    st.caption(f"{total} favorite stocks")

    if not grouped:
        st.info("No favorites yet. Open an industry stock page and tap ☆ Favorite.")
        return

    render_grouped_stock_sections(
        grouped=grouped,
        ticker_getter=lambda ticker: ticker,
        render_stock_cards_fn=render_stock_cards_fn,
        focus_caption_prefix="Focused favorite view",
        empty_message="",
        show_liquidity_context=True,
        stocks_per_row=1,
        chart_height=FAVORITES_COMPACT_CHART_HEIGHT,
        row_layout=FAVORITES_COMPACT_ROW_LAYOUT,
    )
    st.markdown('</div>', unsafe_allow_html=True)
