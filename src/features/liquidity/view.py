"""Liquidity analysis feature for market liquidity and flow visualization."""

import streamlit as st

from ...core.data import get_universe_sectors, list_universes
from ...core.ui.interface import FeatureView
from . import liquidity_refresh_tickers
from .rendering import render_liquidity_chessboard


class LiquidityView(FeatureView):
    """Feature for analyzing market liquidity and capital flows."""

    def get_route_name(self) -> str:
        """Return the feature's unique route name."""
        return "liquidity"

    def get_nav_label(self) -> str:
        return "Liquidity"

    def render_nav_controls(self, selected_universe: str) -> str:
        universes = list_universes()
        if "nav_universe" not in st.session_state or st.session_state.get("nav_universe") not in universes:
            st.session_state["nav_universe"] = selected_universe if selected_universe in universes else universes[0]

        nav_universe_col, nav_sector_col, nav_industry_col = st.columns([4, 4, 4])

        with nav_universe_col:
            new_universe = st.selectbox(
                "Universe",
                universes,
                key="nav_universe",
                label_visibility="collapsed",
            )
        st.session_state.selected_universe = new_universe

        sector_options = ["— all sectors —"] + get_universe_sectors(new_universe)
        current_sector = st.session_state.get("selected_sector", "— all sectors —")
        default_sector = current_sector if current_sector in sector_options else "— all sectors —"
        st.session_state["nav_sector"] = default_sector

        with nav_sector_col:
            selected_sector = st.selectbox(
                "Sector",
                sector_options,
                key="nav_sector",
                label_visibility="collapsed",
            )

        with nav_industry_col:
            st.selectbox(
                "Industry",
                ["— all industries —"],
                disabled=True,
                label_visibility="collapsed",
            )

        if selected_sector == "— all sectors —":
            st.session_state.pop("selected_sector", None)
        else:
            st.session_state.selected_sector = selected_sector
        st.session_state.pop("selected_industry", None)
        st.session_state.view = "liquidity"
        return new_universe

    def get_refresh_tickers(self, selected_universe: str) -> list[str]:
        return liquidity_refresh_tickers(
            selected_universe,
            st.session_state.get("selected_sector"),
            bool(st.session_state.get("liquidity_all_markets", False)),
        )

    def get_render_kwargs(self, selected_universe: str) -> dict[str, str | None]:
        return {
            "universe": selected_universe,
            "sector": st.session_state.get("selected_sector"),
        }

    def render(self, universe: str, sector: str | None = None) -> None:
        """Render the liquidity chessboard visualization.

        Args:
            universe: Selected market universe (e.g., 'S&P 500')
            sector: Optional sector filter for liquidity analysis
        """
        render_liquidity_chessboard(universe, sector)
