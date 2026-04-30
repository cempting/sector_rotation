"""Favorites feature for managing and viewing favorite stocks."""

from ...core.ui.interface import FeatureView
from .rendering import render_favorites_page


class FavoritesView(FeatureView):
    """Feature for managing and viewing favorite stocks."""

    def get_route_name(self) -> str:
        """Return the feature's unique route name."""
        return "favorites"

    def render(self) -> None:
        """Render the favorites page showing all saved favorite stocks."""
        render_favorites_page()
