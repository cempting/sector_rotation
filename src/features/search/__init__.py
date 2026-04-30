"""Search feature for finding and analyzing stocks across universes."""

import streamlit as st

from ...core.data import search_all_universes
from ...core.ui.interface import FeatureView
from .rendering import render_search_results_page


class SearchResultsView(FeatureView):
    """Feature for searching and viewing stock search results."""

    def get_route_name(self) -> str:
        """Return the feature's unique route name."""
        return "search"

    def get_nav_label(self) -> str:
        return "Search"

    def render_nav_controls(self, selected_universe: str) -> str:
        search_input_col, search_action_col = st.columns([9, 1])
        with search_input_col:
            st.text_input(
                "Search",
                key="nav_search_query",
                value=st.session_state.get("search_query", ""),
                placeholder="Ticker, company, sector, or industry",
                label_visibility="collapsed",
            )

        with search_action_col:
            current_query = st.session_state.get("nav_search_query", "").strip()
            has_query = bool(current_query)
            search_matches = len(search_all_universes(current_query, per_universe_limit=12, total_limit=80)) if has_query else 0
            if st.button(
                "🔍",
                key="nav_search",
                help=f"Search stocks ({search_matches} matches)" if has_query else "Search stocks",
                use_container_width=True,
            ):
                self._open_search_view()

        if st.session_state.get("nav_search_query", "").strip() and st.session_state.get("view") != "search":
            # Enter in text_input commits state and triggers rerun; this keeps search auto-open behavior.
            self._open_search_view()

        return selected_universe

    def get_refresh_tickers(self, selected_universe: str) -> list[str]:
        matches = search_all_universes(
            st.session_state.get("search_query", ""),
            per_universe_limit=12,
            total_limit=80,
        )
        return list(dict.fromkeys(match["ticker"] for match in matches))

    def render(self) -> None:
        """Render the search results page showing stocks matching the current query."""
        render_search_results_page()

    @staticmethod
    def _open_search_view() -> None:
        query = st.session_state.get("nav_search_query", "").strip()
        if not query:
            return
        st.session_state.search_query = query
        st.session_state.view = "search"
