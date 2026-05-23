from sector_rotation.src.features.favorites import rendering
from sector_rotation.src.features.favorites.view import FavoritesView


class _ContextStub:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_favorites_nav_controls_initializes_compact_mode_key(monkeypatch):
    session_state = {
        "details_focus_universe": "S&P 500",
        "details_focus_ticker": "MSFT",
    }

    def fake_columns(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_ContextStub() for _ in range(count)]

    def fake_checkbox(label, key=None, **kwargs):
        return session_state.get(key, False)

    monkeypatch.setattr(rendering.st, "session_state", session_state, raising=False)

    from sector_rotation.src.features.favorites import view as favorites_view

    monkeypatch.setattr(favorites_view.st, "session_state", session_state)
    monkeypatch.setattr(favorites_view.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(favorites_view.st, "columns", fake_columns)
    monkeypatch.setattr(favorites_view.st, "download_button", lambda *args, **kwargs: None)
    monkeypatch.setattr(favorites_view.st, "file_uploader", lambda *args, **kwargs: None)
    monkeypatch.setattr(favorites_view.st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(favorites_view, "export_favorites_settings", lambda: "{}")

    selected = FavoritesView().render_nav_controls("S&P 500")

    assert selected == "S&P 500"
    assert "nav_favorites_compact_mode" not in session_state
    assert "favorites_focus_universe" not in session_state
    assert session_state["details_focus_universe"] == "S&P 500"
    assert session_state["details_focus_ticker"] == "MSFT"


def test_render_favorites_page_shows_info_when_empty(monkeypatch):
    calls = {"info": 0, "cards": 0}

    monkeypatch.setattr(rendering, "list_all_favorites", lambda: {})
    monkeypatch.setattr(rendering.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "markdown", lambda *args, **kwargs: None)

    def fake_info(*args, **kwargs):
        calls["info"] += 1

    def fake_cards(**kwargs):
        calls["cards"] += 1

    monkeypatch.setattr(rendering.st, "info", fake_info)

    rendering.render_favorites_page(render_stock_cards_fn=fake_cards)

    assert calls["info"] == 1
    assert calls["cards"] == 0


def test_render_favorites_page_renders_grouped_universes(monkeypatch):
    grouped = {
        "S&P 500": ["AAPL", "MSFT"],
        "NASDAQ": ["AMZN"],
        "NYSE": ["JPM", "GS", "BAC", "MS", "BLK"],
    }
    rendered = []
    markdown_calls = []

    monkeypatch.setattr(rendering, "list_all_favorites", lambda: grouped)
    monkeypatch.setattr(rendering.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "markdown", lambda text, **kwargs: markdown_calls.append(text))

    def fake_cards(**kwargs):
        rendered.append(kwargs)

    rendering.render_favorites_page(render_stock_cards_fn=fake_cards)

    assert "**S&P 500**" in markdown_calls
    assert "**NASDAQ**" in markdown_calls
    assert rendered[0]["tickers"] == ["AAPL", "MSFT"]
    assert rendered[0]["selected_universe"] == "S&P 500"
    assert rendered[0]["show_liquidity_context"] is True
    assert rendered[0]["stocks_per_row"] == 1
    assert rendered[0]["chart_height"] == rendering.FAVORITES_COMPACT_CHART_HEIGHT
    assert rendered[0]["row_layout"] == rendering.FAVORITES_COMPACT_ROW_LAYOUT
    assert rendered[1]["tickers"] == ["AMZN"]
    assert rendered[1]["selected_universe"] == "NASDAQ"
    assert rendered[1]["stocks_per_row"] == 1
    assert rendered[2]["tickers"] == ["JPM", "GS", "BAC", "MS", "BLK"]
    assert rendered[2]["selected_universe"] == "NYSE"
    assert rendered[2]["stocks_per_row"] == 1


def test_render_favorites_page_ignores_unrelated_details_focus(monkeypatch):
    grouped = {"S&P 500": ["AAPL", "MSFT"]}
    rendered = []

    monkeypatch.setattr(rendering, "list_all_favorites", lambda: grouped)
    monkeypatch.setattr(
        rendering.st,
        "session_state",
        {
            "details_focus_universe": "NASDAQ",
            "details_focus_ticker": "NVDA",
        },
    )
    monkeypatch.setattr(rendering.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "markdown", lambda *args, **kwargs: None)

    def fake_cards(**kwargs):
        rendered.append(kwargs)

    rendering.render_favorites_page(render_stock_cards_fn=fake_cards)

    assert len(rendered) == 1
    assert rendered[0]["tickers"] == ["AAPL", "MSFT"]
