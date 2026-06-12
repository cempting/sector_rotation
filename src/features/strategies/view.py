"""Strategies feature view."""

import streamlit as st

from ...core.ui.interface import FeatureView
from .rendering import render_strategies_view


class StrategiesView(FeatureView):
    """Feature for strategy outlines inspired by public investors/traders."""

    def get_route_name(self) -> str:
        return "strategies"

    def get_nav_label(self) -> str:
        return "Strategies"

    def render_nav_controls(self, selected_universe: str) -> str:
        st.session_state.pop("selected_sector", None)
        st.session_state.pop("selected_industry", None)
        st.session_state.pop("selected_stock", None)
        st.session_state.view = "strategies"
        return selected_universe

    def render(self) -> None:
        render_strategies_view()
