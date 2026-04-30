"""Favorites feature for managing and viewing favorite stocks."""

import streamlit as st

from ...core.data import (
    export_favorites_settings,
    import_favorites_settings,
    list_all_favorites,
    list_universes,
)
from ...core.ui.interface import FeatureView
from .rendering import render_favorites_page


class FavoritesView(FeatureView):
    """Feature for managing and viewing favorite stocks."""

    def get_route_name(self) -> str:
        """Return the feature's unique route name."""
        return "favorites"

    def get_nav_label(self) -> str:
        favorite_count = sum(len(tickers) for tickers in list_all_favorites().values())
        return f"Favorites ({favorite_count})"

    def render_nav_controls(self, selected_universe: str) -> str:
        st.markdown('<div class="favorites-controls">', unsafe_allow_html=True)
        export_col, import_file_col, merge_col, import_btn_col = st.columns([2, 4, 1, 2])
        with export_col:
            st.download_button(
                "Export",
                data=export_favorites_settings(),
                file_name="favorites_settings.json",
                mime="application/json",
                use_container_width=False,
                key="nav_favorites_export",
            )
        with import_file_col:
            uploaded_file = st.file_uploader(
                "Import favorites JSON",
                type=["json"],
                key="nav_favorites_import_file",
                label_visibility="collapsed",
            )
        with merge_col:
            merge_import = st.checkbox(
                "Merge",
                value=True,
                key="nav_favorites_import_merge",
            )
        with import_btn_col:
            if st.button("Import", key="nav_favorites_import_apply", use_container_width=False):
                if uploaded_file is None:
                    st.error("Choose a favorites JSON file first.")
                else:
                    try:
                        import_favorites_settings(
                            uploaded_file.getvalue(),
                            merge=merge_import,
                            allowed_universes=set(list_universes()),
                        )
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.success("Favorites imported successfully.")
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return selected_universe

    def get_refresh_tickers(self, selected_universe: str) -> list[str]:
        grouped = list_all_favorites()
        return [ticker for tickers in grouped.values() for ticker in tickers]

    def render(self) -> None:
        """Render the favorites page showing all saved favorite stocks."""
        render_favorites_page()
