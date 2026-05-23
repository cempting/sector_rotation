"""Features plugin system - register and manage feature views."""

from typing import Dict, Type

from ..core.ui.interface import FeatureView


class FeatureRegistry:
    """Central registry for feature views."""

    _features: Dict[str, Type[FeatureView]] = {}
    _instances: Dict[str, FeatureView] = {}
    _initialized: bool = False

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Lazy initialize and register all built-in features."""
        if cls._initialized:
            return

        from .sector_industry_stocks import SectorIndustryStocksView
        from .favorites import FavoritesView
        from .suggestions import SuggestionsView
        from .search import SearchResultsView

        cls.register_feature(SectorIndustryStocksView)
        cls.register_feature(FavoritesView)
        cls.register_feature(SuggestionsView)
        cls.register_feature(SearchResultsView)

        cls._initialized = True

    @classmethod
    def register(cls, route_name: str, feature_class: Type[FeatureView]) -> None:
        """Register a feature view by route name."""
        if not issubclass(feature_class, FeatureView):
            raise TypeError(f"Feature class for route '{route_name}' must inherit FeatureView")
        if route_name in cls._features and cls._features[route_name] is not feature_class:
            raise ValueError(f"Route '{route_name}' already registered")
        cls._features[route_name] = feature_class

    @classmethod
    def register_feature(cls, feature_class: Type[FeatureView]) -> None:
        """Register a feature view by inferring route name from its instance API."""
        route_name = feature_class().get_route_name()
        cls.register(route_name, feature_class)

    @classmethod
    def get_feature(cls, route_name: str) -> FeatureView:
        """Get or create a feature instance."""
        cls._ensure_initialized()
        if route_name not in cls._instances:
            if route_name not in cls._features:
                raise ValueError(f"Feature '{route_name}' not registered")
            cls._instances[route_name] = cls._features[route_name]()
        return cls._instances[route_name]

    @classmethod
    def render_route(cls, route_name: str, **render_kwargs) -> None:
        """Render a route in one call.

        This keeps dashboard/controller code minimal and makes feature usage uniform.
        """
        cls.get_feature(route_name).render(**render_kwargs)

    @classmethod
    def reset(cls) -> None:
        """Clear registry and cached instances (primarily for tests)."""
        cls._features = {}
        cls._instances = {}
        cls._initialized = False

    @classmethod
    def list_routes(cls) -> list[str]:
        """List all registered feature routes."""
        cls._ensure_initialized()
        return sorted(cls._features.keys())


__all__ = ["FeatureRegistry"]
