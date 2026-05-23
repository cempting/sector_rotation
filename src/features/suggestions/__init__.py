"""Suggestions feature for trend and volume based idea discovery."""

import streamlit as st

from ...core.data import list_universes
from ...core.ui.interface import FeatureView
from .rendering import (
    get_suggested_industries,
    get_suggested_industry_stocks,
    render_suggestions_view,
    suggestions_refresh_tickers,
)


class SuggestionsView(FeatureView):
    """Feature for industry and stock suggestions."""

    def get_route_name(self) -> str:
        return "suggestions"

    def get_nav_label(self) -> str:
        return "Suggestions"

    def render_nav_controls(self, selected_universe: str) -> str:
        universes = list_universes()
        if "nav_universe" not in st.session_state or st.session_state.get("nav_universe") not in universes:
            st.session_state["nav_universe"] = selected_universe if selected_universe in universes else universes[0]

        with st.columns([3, 9])[0]:
            new_universe = st.selectbox(
                "Universe",
                universes,
                key="nav_universe",
                label_visibility="collapsed",
            )
        st.session_state.selected_universe = new_universe

        st.session_state.pop("selected_sector", None)
        st.session_state.pop("selected_industry", None)
        st.session_state.view = "suggestions"
        return new_universe

    def get_refresh_tickers(self, selected_universe: str) -> list[str]:
        return suggestions_refresh_tickers(selected_universe)

    def get_render_kwargs(self, selected_universe: str) -> dict[str, str]:
        return {"universe": selected_universe}

    def render(self, universe: str) -> None:
        render_suggestions_view(universe)

    def on_manual_refresh(self, selected_universe: str) -> None:
        _ = selected_universe
        get_suggested_industries.clear()
        get_suggested_industry_stocks.clear()


__all__ = ["SuggestionsView", "render_suggestions_view", "suggestions_refresh_tickers"]
