from sector_rotation.src.features.favorites import rendering


class _ContextStub:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


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
    assert rendered[0]["stocks_per_row"] == 2
    assert rendered[0]["chart_height"] == rendering.FAVORITES_COMPACT_CHART_HEIGHT
    assert rendered[0]["row_layout"] == rendering.FAVORITES_COMPACT_ROW_LAYOUT
    assert rendered[1]["tickers"] == ["AMZN"]
    assert rendered[1]["selected_universe"] == "NASDAQ"
    assert rendered[1]["stocks_per_row"] == 1


def test_render_favorites_page_compact_mode_renders_scorecards(monkeypatch):
    grouped = {"S&P 500": ["AAPL", "MSFT", "NVDA"]}
    markdown_calls = []
    button_calls = []

    monkeypatch.setattr(rendering, "list_all_favorites", lambda: grouped)
    monkeypatch.setattr(rendering, "get_universe_stock_name", lambda u, t: f"Name {t}")
    monkeypatch.setattr(
        rendering,
        "_compact_score_snapshot",
        lambda u, t: {"quality": 80, "growth": 70, "cashflow": 65, "risk": 60, "composite": 72},
    )
    monkeypatch.setattr(rendering.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "markdown", lambda text, **kwargs: markdown_calls.append(text))
    monkeypatch.setattr(rendering.st, "rerun", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "session_state", {})

    def fake_columns(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_ContextStub() for _ in range(count)]

    def fake_button(label, **kwargs):
        button_calls.append((label, kwargs.get("key")))
        return False

    monkeypatch.setattr(rendering.st, "columns", fake_columns)
    monkeypatch.setattr(rendering.st, "button", fake_button)

    rendering.render_favorites_page(compact_mode=True)

    assert "**S&P 500**" in markdown_calls
    assert len([b for b in button_calls if b[0] == "Open Full Analysis"]) == 3


def test_render_favorites_page_compact_mode_dedicated_view(monkeypatch):
    grouped = {"S&P 500": ["AAPL", "MSFT"]}
    rendered = []

    monkeypatch.setattr(rendering, "list_all_favorites", lambda: grouped)
    monkeypatch.setattr(rendering.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "rerun", lambda *args, **kwargs: None)

    def fake_columns(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_ContextStub() for _ in range(count)]

    monkeypatch.setattr(rendering.st, "columns", fake_columns)
    monkeypatch.setattr(rendering.st, "button", lambda *args, **kwargs: False)

    def fake_cards(**kwargs):
        rendered.append(kwargs)

    rendering.render_favorites_page(
        render_stock_cards_fn=fake_cards,
        compact_mode=True,
        focused_universe="S&P 500",
        focused_ticker="MSFT",
    )

    assert len(rendered) == 1
    assert rendered[0]["tickers"] == ["MSFT"]
    assert rendered[0]["selected_universe"] == "S&P 500"
    assert rendered[0]["stocks_per_row"] == 1
