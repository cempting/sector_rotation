"""Search feature for finding and analyzing stocks across universes."""

from ...core.ui.interface import FeatureView
from .rendering import render_search_results_page


class SearchResultsView(FeatureView):
    """Feature for searching and viewing stock search results."""

    def get_route_name(self) -> str:
        """Return the feature's unique route name."""
        return "search"

    def render(self) -> None:
        """Render the search results page showing stocks matching the current query."""
        render_search_results_page()
