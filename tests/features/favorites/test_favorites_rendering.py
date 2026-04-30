from sector_rotation.src.features.favorites import rendering


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

    assert markdown_calls == ["**S&P 500**", "**NASDAQ**"]
    assert rendered[0]["tickers"] == ["AAPL", "MSFT"]
    assert rendered[0]["selected_universe"] == "S&P 500"
    assert rendered[0]["show_liquidity_context"] is True
    assert rendered[0]["stocks_per_row"] == 1
    assert rendered[0]["chart_height"] == rendering.FAVORITES_CHART_HEIGHT
    assert rendered[0]["row_layout"] == rendering.FAVORITES_ROW_LAYOUT
    assert rendered[1]["tickers"] == ["AMZN"]
    assert rendered[1]["selected_universe"] == "NASDAQ"
