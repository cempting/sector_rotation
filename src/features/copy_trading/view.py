"""CopyTrading feature view."""

import streamlit as st

from ...core.ui.interface import FeatureView
from .rendering import render_copy_trading_view


class CopyTradingView(FeatureView):
    """Feature for tracking publicly disclosed activity from notable market participants."""

    def get_route_name(self) -> str:
        return "CopyTrading"

    def get_nav_label(self) -> str:
        return "CopyTrading"

    def render_nav_controls(self, selected_universe: str) -> str:
        st.session_state.pop("selected_sector", None)
        st.session_state.pop("selected_industry", None)
        st.session_state.pop("selected_stock", None)
        st.session_state.view = "CopyTrading"
        return selected_universe

    def render(self) -> None:
        render_copy_trading_view()
