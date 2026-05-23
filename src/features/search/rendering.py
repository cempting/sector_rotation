"""Search feature rendering."""

import streamlit as st

from ...core.data import search_all_universes
from ...core.ui import render_grouped_stock_sections, render_stock_cards


def render_search_results_page(render_stock_cards_fn=None) -> None:
    render_stock_cards_fn = render_stock_cards_fn or render_stock_cards

    query = st.session_state.get("search_query", "")
    matches = search_all_universes(query, per_universe_limit=12, total_limit=80)
    st.subheader("Search · All Universes")
    st.caption(f"Query: {query or '(empty)'}")
    st.caption(f"{len(matches)} matches")

    if not matches:
        st.info("No matching stocks found. Try ticker fragments or company name words.")
        return

    grouped: dict[str, list[dict[str, str]]] = {}
    for match in matches:
        grouped.setdefault(match["universe"], []).append(match)

    def render_group_meta(_universe_name: str, universe_matches: list[dict[str, str]]) -> None:
        sectors = sorted({match.get("sector", "").strip() for match in universe_matches if match.get("sector", "").strip()})
        industries = sorted(
            {match.get("industry", "").strip() for match in universe_matches if match.get("industry", "").strip()}
        )

        labels = []
        if sectors:
            labels.append("Sectors: " + ", ".join(sectors))
        if industries:
            labels.append("Industries: " + ", ".join(industries))
        if labels:
            st.caption(" | ".join(labels))

    render_grouped_stock_sections(
        grouped=grouped,
        ticker_getter=lambda match: match["ticker"],
        render_stock_cards_fn=render_stock_cards_fn,
        focus_caption_prefix="Focused search result view",
        render_group_meta_fn=render_group_meta,
        empty_message="",
    )
