"""
Core UI interfaces - contracts for rendering and feature integration.
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional
from dataclasses import dataclass


@dataclass
class RenderContext:
    """Context passed to feature renderers."""
    selected_universe: str
    session_state: dict[str, Any]
    on_state_change: Optional[Callable[[str, Any], None]] = None


class FeatureView(ABC):
    """Interface for feature-specific views."""
    
    @abstractmethod
    def get_route_name(self) -> str:
        """Return the feature's unique route name (e.g., 'favorites', 'liquidity')."""
        pass
    
    @abstractmethod
    def render(self, *args, **kwargs) -> None:
        """Render the feature view with flexible parameters specific to each feature."""
        pass

    def get_nav_label(self) -> str:
        """Label shown in the dashboard top-row feature selector."""
        return self.get_route_name().replace("_", " ").title()

    def render_nav_controls(self, selected_universe: str) -> str:
        """Render feature-specific controls below the top selector.

        Return the currently selected universe to be used by the dashboard shell.
        """
        return selected_universe

    def get_refresh_tickers(self, selected_universe: str) -> list[str]:
        """Return tickers to refresh for the currently active feature context."""
        return []

    def get_render_kwargs(self, selected_universe: str) -> dict[str, Any]:
        """Return kwargs used when invoking feature `render(...)`."""
        return {}

    def on_manual_refresh(self, selected_universe: str) -> None:
        """Optional hook invoked when the top-nav refresh button is pressed."""
        _ = selected_universe


class ViewRenderer(ABC):
    """Interface for rendering individual UI components."""
    
    @abstractmethod
    def render_stock_cards(
        self,
        tickers: list[str],
        selected_universe: str,
        empty_message: str,
        show_liquidity_context: bool = False,
        stocks_per_row: int = 2,
        chart_height: Optional[float] = None,
        row_layout: Optional[list[tuple[str, float]]] = None,
    ) -> None:
        """Render a grid of stock cards."""
        pass
    
    @abstractmethod
    def render_sector_card(self, name: str, ticker: str) -> None:
        """Render a single sector card."""
        pass
    
    @abstractmethod
    def render_industry_dashboard(self, sector: Optional[str]) -> None:
        """Render an industry dashboard for a sector or market-wide industry view."""
        pass
    
    @abstractmethod
    def render_industry_stock_page(self, sector: Optional[str], industry: str) -> None:
        """Render the industry stock listing page."""
        pass


class DataLayer(ABC):
    """Interface for data access."""
    
    @abstractmethod
    def get_universes(self) -> list[str]:
        """List all available universes."""
        pass
    
    @abstractmethod
    def get_sectors(self, universe: str) -> list[str]:
        """Get sectors in a universe."""
        pass
    
    @abstractmethod
    def get_industries(self, universe: str, sector: str) -> list[str]:
        """Get industries in a sector."""
        pass
    
    @abstractmethod
    def get_universe_tickers(
        self,
        universe: str,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
    ) -> list[str]:
        """Get tickers from a universe with optional filters."""
        pass


class AnalyticsEngine(ABC):
    """Interface for analytics and metrics computation."""
    
    @abstractmethod
    def compute_stock_metrics(self, ticker: str) -> dict[str, Any]:
        """Compute metrics for a ticker."""
        pass
    
    @abstractmethod
    def compute_industry_aggregate(self, tickers: list[str]) -> tuple:
        """Compute aggregated metrics for an industry."""
        pass
