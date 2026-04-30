from sector_rotation.src.features.search import rendering


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def test_render_search_results_page_no_matches(monkeypatch):
    session_state = _SessionState(search_query="abc")
    calls = {"info": 0, "cards": 0}

    monkeypatch.setattr(rendering.st, "session_state", session_state)
    monkeypatch.setattr(rendering, "search_all_universes", lambda *args, **kwargs: [])
    monkeypatch.setattr(rendering.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "markdown", lambda *args, **kwargs: None)

    def fake_info(*args, **kwargs):
        calls["info"] += 1

    def fake_cards(**kwargs):
        calls["cards"] += 1

    monkeypatch.setattr(rendering.st, "info", fake_info)

    rendering.render_search_results_page(render_stock_cards_fn=fake_cards)

    assert calls["info"] == 1
    assert calls["cards"] == 0


def test_render_search_results_page_groups_by_universe(monkeypatch):
    session_state = _SessionState(search_query="a")
    rendered = []
    markdown_calls = []
    captions = []

    matches = [
        {"universe": "S&P 500", "ticker": "AAPL", "sector": "Technology", "industry": "Hardware"},
        {"universe": "S&P 500", "ticker": "MSFT", "sector": "Technology", "industry": "Software"},
        {"universe": "NASDAQ", "ticker": "AMZN", "sector": "Consumer Disc", "industry": "Internet Retail"},
    ]

    monkeypatch.setattr(rendering.st, "session_state", session_state)
    monkeypatch.setattr(rendering, "search_all_universes", lambda *args, **kwargs: matches)
    monkeypatch.setattr(rendering.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "caption", lambda text, *args, **kwargs: captions.append(text))
    monkeypatch.setattr(rendering.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "markdown", lambda text, **kwargs: markdown_calls.append(text))

    def fake_cards(**kwargs):
        rendered.append(kwargs)

    rendering.render_search_results_page(render_stock_cards_fn=fake_cards)

    assert markdown_calls == ["**S&P 500**", "**NASDAQ**"]
    assert rendered == [
        {"tickers": ["AAPL", "MSFT"], "selected_universe": "S&P 500", "empty_message": ""},
        {"tickers": ["AMZN"], "selected_universe": "NASDAQ", "empty_message": ""},
    ]
    assert any("Sectors: Technology" in c for c in captions)
    assert any("Industries: Hardware, Software" in c for c in captions)
