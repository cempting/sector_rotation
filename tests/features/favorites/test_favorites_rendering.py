from sector_rotation.src.features.favorites import rendering


class _ContextStub:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _UploadedFileStub:
    def __init__(self, payload: bytes):
        self._payload = payload

    def getvalue(self):
        return self._payload


def test_render_favorites_page_shows_info_when_empty(monkeypatch):
    calls = {"info": 0, "cards": 0}

    monkeypatch.setattr(rendering, "list_all_favorites", lambda: {})
    monkeypatch.setattr(rendering.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "columns", lambda spec: (_ContextStub(), _ContextStub()))
    monkeypatch.setattr(rendering.st, "download_button", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "file_uploader", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "checkbox", lambda *args, **kwargs: True)
    monkeypatch.setattr(rendering.st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(rendering.st, "error", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "success", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "rerun", lambda *args, **kwargs: None)

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
    monkeypatch.setattr(rendering.st, "columns", lambda spec: (_ContextStub(), _ContextStub()))
    monkeypatch.setattr(rendering.st, "download_button", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "file_uploader", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "checkbox", lambda *args, **kwargs: True)
    monkeypatch.setattr(rendering.st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(rendering.st, "error", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "success", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "rerun", lambda *args, **kwargs: None)

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


def test_render_favorites_page_import_success(monkeypatch):
    calls = {"success": 0, "rerun": 0}

    monkeypatch.setattr(rendering, "list_all_favorites", lambda: {"S&P 500": ["AAPL"]})
    monkeypatch.setattr(rendering, "export_favorites_settings", lambda: "{}")
    monkeypatch.setattr(rendering, "import_favorites_settings", lambda payload, merge: (2, 3))

    monkeypatch.setattr(rendering.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "columns", lambda spec: (_ContextStub(), _ContextStub()))
    monkeypatch.setattr(rendering.st, "download_button", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rendering.st,
        "file_uploader",
        lambda *args, **kwargs: _UploadedFileStub(b'{"S&P 500": ["AAPL"]}'),
    )
    monkeypatch.setattr(rendering.st, "checkbox", lambda *args, **kwargs: True)
    monkeypatch.setattr(rendering.st, "button", lambda *args, **kwargs: True)
    monkeypatch.setattr(rendering.st, "error", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "success", lambda *args, **kwargs: calls.__setitem__("success", calls["success"] + 1))
    monkeypatch.setattr(rendering.st, "rerun", lambda *args, **kwargs: calls.__setitem__("rerun", calls["rerun"] + 1))

    rendering.render_favorites_page(render_stock_cards_fn=lambda **kwargs: None)

    assert calls["success"] == 1
    assert calls["rerun"] == 1


def test_render_favorites_page_import_invalid_payload(monkeypatch):
    calls = {"error": 0}

    monkeypatch.setattr(rendering, "list_all_favorites", lambda: {"S&P 500": ["AAPL"]})
    monkeypatch.setattr(rendering, "export_favorites_settings", lambda: "{}")

    def raise_invalid(payload, merge):
        raise ValueError("Invalid favorites JSON payload")

    monkeypatch.setattr(rendering, "import_favorites_settings", raise_invalid)

    monkeypatch.setattr(rendering.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "columns", lambda spec: (_ContextStub(), _ContextStub()))
    monkeypatch.setattr(rendering.st, "download_button", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        rendering.st,
        "file_uploader",
        lambda *args, **kwargs: _UploadedFileStub(b"not-json"),
    )
    monkeypatch.setattr(rendering.st, "checkbox", lambda *args, **kwargs: True)
    monkeypatch.setattr(rendering.st, "button", lambda *args, **kwargs: True)
    monkeypatch.setattr(rendering.st, "success", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "rerun", lambda *args, **kwargs: None)
    monkeypatch.setattr(rendering.st, "error", lambda *args, **kwargs: calls.__setitem__("error", calls["error"] + 1))

    rendering.render_favorites_page(render_stock_cards_fn=lambda **kwargs: None)

    assert calls["error"] == 1
