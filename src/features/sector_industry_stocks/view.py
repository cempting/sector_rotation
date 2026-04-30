"""Sector/Industry/Stocks browsing feature."""

from ...core.ui.interface import FeatureView
from .rendering import render_industry_dashboard, render_industry_stock_page, render_sector_grid


class SectorIndustryStocksView(FeatureView):
    """Feature for browsing and analyzing sectors, industries, and stocks."""

    def get_route_name(self) -> str:
        """Return the feature's unique route name."""
        return "sector_industry_stocks"

    def render(self, universe: str, sector: str | None = None, industry: str | None = None) -> None:
        """Render the appropriate sector/industry/stocks view based on selected scope.
        
        Args:
            universe: Selected market universe (e.g., 'S&P 500')
            sector: Optional selected sector name; if None, renders sector grid
            industry: Optional selected industry; only valid if sector is also set
        """
        if sector and industry:
            render_industry_stock_page(sector, industry)
        elif sector:
            render_industry_dashboard(sector)
        else:
            render_sector_grid(universe)
