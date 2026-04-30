"""Search feature rendering."""

import streamlit as st

from ...core.data import search_all_universes
from ...core.ui import render_stock_cards


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

    for universe_name, universe_matches in grouped.items():
        st.markdown(f"**{universe_name}**")

        tickers = list(dict.fromkeys(match["ticker"] for match in universe_matches))
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

        render_stock_cards_fn(
            tickers=tickers,
            selected_universe=universe_name,
            empty_message="",
        )
