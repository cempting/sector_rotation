from sector_rotation.src import dashboard, renderers
from sector_rotation.src.features import FeatureRegistry
from sector_rotation.src.features.sector_industry_stocks import rendering as sector_rendering
from sector_rotation.src.features.sector_industry_stocks import view as sector_view
from sector_rotation.src.features.sector_industry_stocks.view import SectorIndustryStocksView


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _ContextStub:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_feature_registry_instantiates_builtin_routes():
    original_features = FeatureRegistry._features.copy()
    original_instances = FeatureRegistry._instances.copy()
    original_initialized = FeatureRegistry._initialized

    try:
        FeatureRegistry.reset()

        routes = FeatureRegistry.list_routes()

        assert routes == ["favorites", "liquidity", "search", "sector_industry_stocks"]
        for route in routes:
            feature = FeatureRegistry.get_feature(route)
            assert feature.get_route_name() == route
    finally:
        FeatureRegistry._features = original_features
        FeatureRegistry._instances = original_instances
        FeatureRegistry._initialized = original_initialized


def test_sector_view_industry_dashboard_uses_renderer_wrapper(monkeypatch):
    calls = {}

    def fake_render(sector):
        calls["sector"] = sector

    monkeypatch.setattr(sector_view, "render_industry_dashboard", fake_render)

    SectorIndustryStocksView().render(universe="S&P 500", sector="Information Technology")

    assert calls["sector"] == "Information Technology"


def test_renderers_industry_dashboard_supplies_callbacks(monkeypatch):
    calls = {}

    def fake_render(sector, compute_return_vol_rr=None, render_data_card_fn=None, open_industry_stocks_fn=None):
        calls["sector"] = sector
        calls["compute_return_vol_rr"] = compute_return_vol_rr
        calls["render_data_card"] = render_data_card_fn
        calls["open_industry_stocks"] = open_industry_stocks_fn

    monkeypatch.setattr(sector_rendering, "render_industry_dashboard", fake_render)

    renderers.render_industry_dashboard("Information Technology")

    assert calls["sector"] == "Information Technology"
    assert callable(calls["compute_return_vol_rr"])
    assert callable(calls["render_data_card"])
    assert callable(calls["open_industry_stocks"])


def test_open_search_view_ignores_empty_query(monkeypatch):
    session_state = _SessionState(
        nav_search_query="   ",
        nav_feature="browse",
        search_query="MSFT",
        view="sector",
    )

    monkeypatch.setattr(dashboard.st, "session_state", session_state)

    dashboard._open_search_view()

    assert session_state["view"] == "sector"
    assert session_state["search_query"] == "MSFT"
    assert session_state["nav_feature"] == "browse"


def test_open_search_view_sets_query_and_switches_view(monkeypatch):
    session_state = _SessionState(nav_search_query="  AAPL  ", view="sector", nav_feature="browse")

    monkeypatch.setattr(dashboard.st, "session_state", session_state)

    dashboard._open_search_view()

    assert session_state["search_query"] == "AAPL"
    assert session_state["view"] == "search"
    assert session_state["nav_feature"] == "search"


def test_render_top_nav_delegates_controls_to_active_feature(monkeypatch):
    session_state = _SessionState(view="search", nav_feature="search")
    calls = {"nav": 0}

    class _StubFeature:
        def get_nav_label(self):
            return "Stub"

        def render_nav_controls(self, selected_universe):
            calls["nav"] += 1
            return selected_universe or "S&P 500"

        def get_refresh_tickers(self, selected_universe):
            return []

        def get_render_kwargs(self, selected_universe):
            return {}

    def fake_get_feature(route):
        return _StubFeature()

    def fake_columns(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_ContextStub() for _ in range(count)]

    def fake_button(label, **kwargs):
        return False

    def fake_radio(label, options, key=None, **kwargs):
        value = session_state.get(key, options[0])
        if key is not None:
            session_state[key] = value
        return value

    monkeypatch.setattr(dashboard.st, "session_state", session_state)
    monkeypatch.setattr(dashboard.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "button", fake_button)
    monkeypatch.setattr(dashboard.st, "radio", fake_radio)
    monkeypatch.setattr(dashboard.st, "columns", fake_columns)
    monkeypatch.setattr(dashboard.FeatureRegistry, "get_feature", fake_get_feature)
    monkeypatch.setattr(dashboard, "list_universes", lambda: ["S&P 500"])

    selected_universe = dashboard._render_top_nav()

    assert calls["nav"] == 1
    assert selected_universe == "S&P 500"


def test_render_top_nav_uses_feature_refresh_tickers(monkeypatch):
    session_state = _SessionState(view="favorites", nav_feature="favorites")
    calls = {"cleared": None}

    class _StubFeature:
        def get_nav_label(self):
            return "Stub"

        def render_nav_controls(self, selected_universe):
            return "S&P 500"

        def get_refresh_tickers(self, selected_universe):
            return ["AAPL", "MSFT"]

        def get_render_kwargs(self, selected_universe):
            return {}

    def fake_get_feature(route):
        return _StubFeature()

    def fake_columns(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_ContextStub() for _ in range(count)]

    def fake_button(label, **kwargs):
        return label == "🔄"

    def fake_radio(label, options, key=None, **kwargs):
        value = session_state.get(key, options[0])
        if key is not None:
            session_state[key] = value
        return value

    monkeypatch.setattr(dashboard.st, "session_state", session_state)
    monkeypatch.setattr(dashboard.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "button", fake_button)
    monkeypatch.setattr(dashboard.st, "radio", fake_radio)
    monkeypatch.setattr(dashboard.st, "columns", fake_columns)
    monkeypatch.setattr(dashboard.st, "rerun", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.FeatureRegistry, "get_feature", fake_get_feature)
    monkeypatch.setattr(dashboard, "list_universes", lambda: ["S&P 500"])
    monkeypatch.setattr(dashboard, "clear_tickers_cache", lambda tickers: calls.__setitem__("cleared", tickers))

    dashboard._render_top_nav()

    assert calls["cleared"] == ["AAPL", "MSFT"]
