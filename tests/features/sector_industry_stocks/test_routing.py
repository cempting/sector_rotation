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
        nav_view_mode="browse",
        search_query="MSFT",
        view="sector",
    )

    monkeypatch.setattr(dashboard.st, "session_state", session_state)

    dashboard._open_search_view()

    assert session_state["view"] == "sector"
    assert session_state["search_query"] == "MSFT"
    assert session_state["nav_view_mode"] == "browse"


def test_open_search_view_sets_query_and_switches_view(monkeypatch):
    session_state = _SessionState(nav_search_query="  AAPL  ", view="sector", nav_view_mode="browse")

    monkeypatch.setattr(dashboard.st, "session_state", session_state)

    dashboard._open_search_view()

    assert session_state["search_query"] == "AAPL"
    assert session_state["view"] == "search"
    assert session_state["nav_view_mode"] == "browse"


def test_render_top_nav_leaves_search_button_clickable(monkeypatch):
    session_state = _SessionState(view="sector", search_query="", nav_search_query="AAPL")
    button_calls = []

    def fake_columns(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_ContextStub() for _ in range(count)]

    def fake_button(label, **kwargs):
        button_calls.append((label, kwargs))
        return False

    def fake_selectbox(label, options, key=None, disabled=False, **kwargs):
        value = session_state.get(key, options[0])
        if key is not None:
            session_state[key] = value
        return value

    def fake_radio(label, options, key=None, **kwargs):
        value = session_state.get(key, options[0])
        if key is not None:
            session_state[key] = value
        return value

    monkeypatch.setattr(dashboard.st, "session_state", session_state)
    monkeypatch.setattr(dashboard.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "text_input", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.st, "button", fake_button)
    monkeypatch.setattr(dashboard.st, "selectbox", fake_selectbox)
    monkeypatch.setattr(dashboard.st, "radio", fake_radio)
    monkeypatch.setattr(dashboard.st, "columns", fake_columns)
    monkeypatch.setattr(dashboard.st, "popover", lambda *args, **kwargs: _ContextStub())
    monkeypatch.setattr(dashboard.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard, "list_universes", lambda: ["S&P 100"])
    monkeypatch.setattr(dashboard, "get_universe_sectors", lambda universe: [])
    monkeypatch.setattr(dashboard, "get_universe_industries", lambda universe, sector: [])
    monkeypatch.setattr(dashboard, "get_universe_tickers", lambda *args, **kwargs: [])
    monkeypatch.setattr(dashboard, "get_sector_industry_counts", lambda universe, sector: {})
    monkeypatch.setattr(dashboard, "get_universe_sector_stock_count", lambda universe, sector: 0)
    monkeypatch.setattr(dashboard, "search_all_universes", lambda *args, **kwargs: [{"ticker": "AAPL"}])
    monkeypatch.setattr(dashboard, "list_all_favorites", lambda: {})
    monkeypatch.setattr(dashboard, "total_favorites_count", lambda: 0)
    monkeypatch.setattr(dashboard, "liquidity_refresh_tickers", lambda *args, **kwargs: [])

    dashboard._render_top_nav()

    search_button = next(kwargs for label, kwargs in button_calls if label == "🔍")
    assert search_button["on_click"] is dashboard._open_search_view
    assert search_button.get("disabled", False) is False