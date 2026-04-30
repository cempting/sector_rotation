"""Liquidity analysis feature for market liquidity and flow visualization."""

from ...core.ui.interface import FeatureView
from .rendering import render_liquidity_chessboard


class LiquidityView(FeatureView):
    """Feature for analyzing market liquidity and capital flows."""

    def get_route_name(self) -> str:
        """Return the feature's unique route name."""
        return "liquidity"

    def render(self, universe: str, sector: str | None = None) -> None:
        """Render the liquidity chessboard visualization.
        
        Args:
            universe: Selected market universe (e.g., 'S&P 500')
            sector: Optional sector filter for liquidity analysis
        """
        render_liquidity_chessboard(universe, sector)
