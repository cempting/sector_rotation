import pandas as pd

from sector_rotation.src import dashboard, renderers
from sector_rotation.src.core.analytics import app_control
from sector_rotation.src.constants import resolve_industry_proxy_ticker
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

        assert routes == ["favorites", "search", "sector_industry_stocks", "suggestions"]
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
    monkeypatch.setattr(dashboard, "get_download_status", lambda max_age_seconds=None: None)

    selected_universe = dashboard._render_top_nav()

    assert calls["nav"] == 1
    assert selected_universe == "S&P 500"


def test_render_top_nav_uses_feature_refresh_tickers(monkeypatch):
    session_state = _SessionState(view="favorites", nav_feature="favorites")
    calls = {"cleared": None, "manual_refresh": None}

    class _StubFeature:
        def get_nav_label(self):
            return "Stub"

        def render_nav_controls(self, selected_universe):
            return "S&P 500"

        def get_refresh_tickers(self, selected_universe):
            return ["AAPL", "MSFT"]

        def get_render_kwargs(self, selected_universe):
            return {}

        def on_manual_refresh(self, selected_universe):
            calls["manual_refresh"] = selected_universe

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
    monkeypatch.setattr(dashboard, "get_download_status", lambda max_age_seconds=None: None)

    dashboard._render_top_nav()

    assert calls["cleared"] == ["AAPL", "MSFT"]
    assert calls["manual_refresh"] == "S&P 500"


def test_render_top_nav_skips_refresh_tickers_when_not_clicked(monkeypatch):
    session_state = _SessionState(view="favorites", nav_feature="favorites")
    calls = {"refresh_called": 0, "cleared": None}

    class _StubFeature:
        def get_nav_label(self):
            return "Stub"

        def render_nav_controls(self, selected_universe):
            return "S&P 500"

        def get_refresh_tickers(self, selected_universe):
            calls["refresh_called"] += 1
            return ["AAPL", "MSFT"]

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
    monkeypatch.setattr(dashboard.st, "rerun", lambda *args, **kwargs: None)
    monkeypatch.setattr(dashboard.FeatureRegistry, "get_feature", fake_get_feature)
    monkeypatch.setattr(dashboard, "list_universes", lambda: ["S&P 500"])
    monkeypatch.setattr(dashboard, "clear_tickers_cache", lambda tickers: calls.__setitem__("cleared", tickers))
    monkeypatch.setattr(dashboard, "get_download_status", lambda max_age_seconds=None: None)

    dashboard._render_top_nav()

    assert calls["refresh_called"] == 0
    assert calls["cleared"] is None


def test_sector_nav_controls_support_stock_dropdown(monkeypatch):
    session_state = _SessionState(
        selected_universe="S&P 500",
        selected_sector="Technology",
        selected_industry="Software",
        selected_stock="MSFT",
        view="sector",
    )

    def fake_columns(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_ContextStub() for _ in range(count)]

    def fake_popover(*args, **kwargs):
        return _ContextStub()

    def fake_selectbox(label, options, key=None, **kwargs):
        value = session_state.get(key, options[0]) if key else options[0]
        if key is not None:
            session_state[key] = value
        return value

    monkeypatch.setattr(sector_view.st, "session_state", session_state)
    monkeypatch.setattr(sector_view.st, "columns", fake_columns)
    monkeypatch.setattr(sector_view.st, "selectbox", fake_selectbox)
    monkeypatch.setattr(sector_view.st, "popover", fake_popover)
    monkeypatch.setattr(sector_view.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(sector_view.st, "caption", lambda *args, **kwargs: None)

    monkeypatch.setattr(sector_view, "list_universes", lambda: ["S&P 500"])
    monkeypatch.setattr(sector_view, "get_universe_sectors", lambda u: ["Technology"])
    monkeypatch.setattr(sector_view, "get_universe_industries", lambda u, s: ["Software"])
    monkeypatch.setattr(
        sector_view,
        "get_universe_tickers",
        lambda u, sector=None, industry=None: ["MSFT", "AAPL"],
    )
    monkeypatch.setattr(sector_view, "get_sector_industry_counts", lambda u, s: {"Software": 2})
    monkeypatch.setattr(sector_view, "get_universe_sector_stock_count", lambda u, s: 2)

    selected_universe = SectorIndustryStocksView().render_nav_controls("S&P 500")

    assert selected_universe == "S&P 500"
    assert session_state["selected_sector"] == "Technology"
    assert session_state["selected_industry"] == "Software"
    assert session_state["selected_stock"] == "MSFT"
    assert session_state["view"] == "industry_stocks"


def test_sector_view_refresh_tickers_honors_selected_stock(monkeypatch):
    session_state = _SessionState(
        view="industry_stocks",
        selected_sector="Technology",
        selected_industry="Software",
        selected_stock="MSFT",
    )
    monkeypatch.setattr(sector_view.st, "session_state", session_state)

    tickers = SectorIndustryStocksView().get_refresh_tickers("S&P 500")

    assert tickers == ["MSFT"]


def test_sector_nav_controls_without_sectors_goes_directly_to_industries(monkeypatch):
    session_state = _SessionState(
        selected_universe="Custom Universe",
        selected_industry="Semiconductors",
        selected_stock="NVDA",
        view="sector",
    )

    def fake_columns(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_ContextStub() for _ in range(count)]

    def fake_selectbox(label, options, key=None, **kwargs):
        value = session_state.get(key, options[0]) if key else options[0]
        if key is not None:
            session_state[key] = value
        return value

    monkeypatch.setattr(sector_view.st, "session_state", session_state)
    monkeypatch.setattr(sector_view.st, "columns", fake_columns)
    monkeypatch.setattr(sector_view.st, "selectbox", fake_selectbox)
    monkeypatch.setattr(sector_view.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(sector_view.st, "caption", lambda *args, **kwargs: None)

    monkeypatch.setattr(sector_view, "list_universes", lambda: ["Custom Universe"])
    monkeypatch.setattr(sector_view, "get_universe_sectors", lambda u: [])
    monkeypatch.setattr(sector_view, "get_universe_industries", lambda u, s=None: ["Semiconductors"])
    monkeypatch.setattr(
        sector_view,
        "get_universe_tickers",
        lambda u, sector=None, industry=None: ["NVDA", "AMD"],
    )

    selected_universe = SectorIndustryStocksView().render_nav_controls("Custom Universe")

    assert selected_universe == "Custom Universe"
    assert "selected_sector" not in session_state
    assert session_state["selected_industry"] == "Semiconductors"
    assert session_state["selected_stock"] == "NVDA"
    assert session_state["view"] == "industry_stocks"


def test_sector_nav_controls_honors_new_nav_sector_selection(monkeypatch):
    session_state = _SessionState(
        selected_universe="S&P 500",
        selected_sector="Technology",
        nav_sector="Energy",
        view="industry",
    )

    def fake_columns(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_ContextStub() for _ in range(count)]

    def fake_popover(*args, **kwargs):
        return _ContextStub()

    def fake_selectbox(label, options, key=None, **kwargs):
        value = session_state.get(key, options[0]) if key else options[0]
        if key is not None:
            session_state[key] = value
        return value

    monkeypatch.setattr(sector_view.st, "session_state", session_state)
    monkeypatch.setattr(sector_view.st, "columns", fake_columns)
    monkeypatch.setattr(sector_view.st, "selectbox", fake_selectbox)
    monkeypatch.setattr(sector_view.st, "popover", fake_popover)
    monkeypatch.setattr(sector_view.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(sector_view.st, "caption", lambda *args, **kwargs: None)

    monkeypatch.setattr(sector_view, "list_universes", lambda: ["S&P 500"])
    monkeypatch.setattr(sector_view, "get_universe_sectors", lambda u: ["Technology", "Energy"])
    monkeypatch.setattr(sector_view, "get_universe_industries", lambda u, s: [])
    monkeypatch.setattr(sector_view, "get_universe_tickers", lambda u, sector=None, industry=None: [])
    monkeypatch.setattr(sector_view, "get_sector_industry_counts", lambda u, s: {})
    monkeypatch.setattr(sector_view, "get_universe_sector_stock_count", lambda u, s: 0)

    selected_universe = SectorIndustryStocksView().render_nav_controls("S&P 500")

    assert selected_universe == "S&P 500"
    assert session_state["selected_sector"] == "Energy"
    assert session_state["view"] == "industry"


def test_active_selection_label_universe_only(monkeypatch):
    session_state = _SessionState()
    monkeypatch.setattr(sector_view.st, "session_state", session_state)

    label = SectorIndustryStocksView._active_selection_label("S&P 500")

    assert label == "Active selection - Universe: S&P 500"


def test_active_selection_label_full_scope(monkeypatch):
    session_state = _SessionState(
        selected_sector="Technology",
        selected_industry="Software",
        selected_stock="MSFT",
    )
    monkeypatch.setattr(sector_view.st, "session_state", session_state)

    label = SectorIndustryStocksView._active_selection_label("S&P 500")

    assert label == (
        "Active selection - Universe: S&P 500 | Sector: Technology | "
        "Industry: Software | Stock: MSFT"
    )


def test_open_sector_industries_syncs_nav_and_selection(monkeypatch):
    session_state = _SessionState(
        nav_feature="browse",
        view="sector",
        selected_industry="Old Industry",
        nav_industry="Old Industry",
        selected_stock="OLD",
        nav_stock="OLD",
    )
    monkeypatch.setattr(sector_rendering.st, "session_state", session_state)

    sector_rendering.open_sector_industries("Energy")

    assert session_state["nav_feature"] == "browse"
    assert session_state["view"] == "industry"
    assert session_state["selected_sector"] == "Energy"
    assert session_state["nav_sector"] == "Energy"
    assert "selected_industry" not in session_state
    assert "nav_industry" not in session_state
    assert "selected_stock" not in session_state
    assert "nav_stock" not in session_state


def test_button_selection_state_survives_nav_controls(monkeypatch):
    session_state = _SessionState(selected_universe="S&P 500", nav_universe="S&P 500", view="sector")

    def fake_columns(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_ContextStub() for _ in range(count)]

    def fake_popover(*args, **kwargs):
        return _ContextStub()

    def fake_selectbox(label, options, key=None, **kwargs):
        value = session_state.get(key, options[0]) if key else options[0]
        if key is not None:
            session_state[key] = value
        return value

    monkeypatch.setattr(sector_view.st, "session_state", session_state)
    monkeypatch.setattr(sector_view.st, "columns", fake_columns)
    monkeypatch.setattr(sector_view.st, "selectbox", fake_selectbox)
    monkeypatch.setattr(sector_view.st, "popover", fake_popover)
    monkeypatch.setattr(sector_view.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(sector_view.st, "caption", lambda *args, **kwargs: None)

    monkeypatch.setattr(sector_view, "list_universes", lambda: ["S&P 500"])
    monkeypatch.setattr(sector_view, "get_universe_sectors", lambda u: ["Technology", "Energy"])
    monkeypatch.setattr(sector_view, "get_universe_industries", lambda u, s: ["Software", "Semiconductors"])
    monkeypatch.setattr(sector_view, "get_universe_tickers", lambda u, sector=None, industry=None: ["AAPL", "MSFT"])
    monkeypatch.setattr(sector_view, "get_sector_industry_counts", lambda u, s: {"Software": 2})
    monkeypatch.setattr(sector_view, "get_universe_sector_stock_count", lambda u, s: 2)

    sector_rendering.open_sector_industries("Energy")
    app_control.open_industry_stocks("Energy", "Semiconductors")
    selected_universe = SectorIndustryStocksView().render_nav_controls("S&P 500")

    assert selected_universe == "S&P 500"
    assert session_state["selected_sector"] == "Energy"
    assert session_state["nav_sector"] == "Energy"
    assert session_state["selected_industry"] == "Semiconductors"
    assert session_state["nav_industry"] == "Semiconductors"
    assert session_state["view"] == "industry_stocks"


def test_selection_smoke_view_industries_then_view_stocks_updates_active_label(monkeypatch):
    session_state = _SessionState(
        selected_universe="S&P 500",
        nav_universe="S&P 500",
        view="sector",
    )

    monkeypatch.setattr(sector_rendering.st, "session_state", session_state)
    monkeypatch.setattr(app_control.st, "session_state", session_state)
    monkeypatch.setattr(sector_view.st, "session_state", session_state)

    label0 = SectorIndustryStocksView._active_selection_label("S&P 500")
    assert label0 == "Active selection - Universe: S&P 500"

    # Simulate clicking "View Industries" on a sector card.
    sector_rendering.open_sector_industries("Energy")
    label1 = SectorIndustryStocksView._active_selection_label("S&P 500")
    assert label1 == "Active selection - Universe: S&P 500 | Sector: Energy"
    assert session_state["view"] == "industry"

    # Simulate clicking "View Stocks" on an industry card.
    app_control.open_industry_stocks("Energy", "Oil & Gas")
    label2 = SectorIndustryStocksView._active_selection_label("S&P 500")
    assert label2 == "Active selection - Universe: S&P 500 | Sector: Energy | Industry: Oil & Gas"
    assert session_state["view"] == "industry_stocks"


def test_selection_smoke_no_sector_universe_view_stocks_updates_active_label(monkeypatch):
    session_state = _SessionState(
        selected_universe="Custom Universe",
        nav_universe="Custom Universe",
        view="industry",
    )

    monkeypatch.setattr(app_control.st, "session_state", session_state)
    monkeypatch.setattr(sector_view.st, "session_state", session_state)

    label0 = SectorIndustryStocksView._active_selection_label("Custom Universe")
    assert label0 == "Active selection - Universe: Custom Universe"

    # Simulate clicking "View Stocks" in a universe without sector breakdown.
    app_control.open_industry_stocks(None, "Semiconductors")

    label1 = SectorIndustryStocksView._active_selection_label("Custom Universe")
    assert label1 == "Active selection - Universe: Custom Universe | Industry: Semiconductors"
    assert session_state["view"] == "industry_stocks"
    assert "selected_sector" not in session_state
    assert "nav_sector" not in session_state


def test_sector_view_without_sectors_renders_industry_dashboard(monkeypatch):
    calls = {}

    monkeypatch.setattr(sector_view, "get_universe_sectors", lambda u: [])

    def fake_render(sector):
        calls["sector"] = sector

    monkeypatch.setattr(sector_view, "render_industry_dashboard", fake_render)

    SectorIndustryStocksView().render(universe="Custom Universe")

    assert calls["sector"] is None


def test_resolve_industry_proxy_ticker_uses_representative_etfs():
    assert resolve_industry_proxy_ticker("S&P 500", "Technology", "Semiconductors") == "SMH"
    assert resolve_industry_proxy_ticker("STOXX Europe 600", "Financial Services", "Banks") == "EXV1.DE"


def test_industry_dashboard_uses_proxy_etf_data_when_available(monkeypatch):
    session_state = _SessionState(selected_universe="S&P 500")
    captured = {}

    def fake_columns(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_ContextStub() for _ in range(count)]

    def fake_popover(*args, **kwargs):
        return _ContextStub()

    def fake_spinner(*args, **kwargs):
        return _ContextStub()

    def fake_render_data_card(**kwargs):
        captured["title"] = kwargs["title"]
        captured["legend_label"] = kwargs["chart_params"]["legend_label"]

    monkeypatch.setattr(sector_rendering.st, "session_state", session_state)
    monkeypatch.setattr(sector_rendering.st, "columns", fake_columns)
    monkeypatch.setattr(sector_rendering.st, "popover", fake_popover)
    monkeypatch.setattr(sector_rendering.st, "spinner", fake_spinner)
    monkeypatch.setattr(sector_rendering.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(sector_rendering.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(sector_rendering.st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(sector_rendering.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(sector_rendering, "get_sector_industry_counts", lambda universe, sector: {"Semiconductors": 12})
    monkeypatch.setattr(sector_rendering, "get_universe_tickers", lambda *args, **kwargs: ["NVDA", "AMD"])
    monkeypatch.setattr(
        sector_rendering,
        "fetch_sector_data",
        lambda ticker, period="1y": pd.DataFrame({"Close": [100.0, 101.0, 102.0], "Volume": [10, 12, 14]}),
    )
    monkeypatch.setattr(sector_rendering, "compute_industry_aggregate", lambda tickers: (_ for _ in ()).throw(AssertionError("should use proxy ETF data")))
    monkeypatch.setattr(sector_rendering, "render_data_card", fake_render_data_card)

    sector_rendering.render_industry_dashboard("Technology")

    assert captured["title"] == "Semiconductors (SMH)"
    assert captured["legend_label"] == "SMH"
