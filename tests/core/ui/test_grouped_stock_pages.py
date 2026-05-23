from sector_rotation.src.core.ui import grouped_stock_pages


def test_render_grouped_stock_sections_renders_focus_caption_and_narrows(monkeypatch):
    session_state = {
        "details_focus_universe": "NASDAQ",
        "details_focus_ticker": "NVDA",
    }
    markdown_calls = []
    caption_calls = []
    cards_calls = []

    grouped = {
        "S&P 500": ["AAPL", "MSFT"],
        "NASDAQ": ["NVDA", "AMZN"],
    }

    monkeypatch.setattr(grouped_stock_pages.st, "session_state", session_state)
    monkeypatch.setattr(grouped_stock_pages.st, "markdown", lambda text, **kwargs: markdown_calls.append(text))
    monkeypatch.setattr(grouped_stock_pages.st, "caption", lambda text, **kwargs: caption_calls.append(text))

    grouped_stock_pages.render_grouped_stock_sections(
        grouped=grouped,
        ticker_getter=lambda ticker: ticker,
        render_stock_cards_fn=lambda **kwargs: cards_calls.append(kwargs),
        focus_caption_prefix="Focused grouped view",
        empty_message="",
    )

    assert any("Focused grouped view · NVDA · NASDAQ" in msg for msg in caption_calls)
    assert markdown_calls == ["**NASDAQ**"]
    assert cards_calls == [
        {"tickers": ["NVDA", "AMZN"], "selected_universe": "NASDAQ", "empty_message": ""}
    ]


def test_render_grouped_stock_sections_forwards_optional_kwargs(monkeypatch):
    session_state = {}
    cards_calls = []

    grouped = {
        "S&P 500": ["AAPL", "MSFT"],
    }

    monkeypatch.setattr(grouped_stock_pages.st, "session_state", session_state)
    monkeypatch.setattr(grouped_stock_pages.st, "markdown", lambda *args, **kwargs: None)
    monkeypatch.setattr(grouped_stock_pages.st, "caption", lambda *args, **kwargs: None)

    grouped_stock_pages.render_grouped_stock_sections(
        grouped=grouped,
        ticker_getter=lambda ticker: ticker,
        render_stock_cards_fn=lambda **kwargs: cards_calls.append(kwargs),
        focus_caption_prefix="Focused grouped view",
        empty_message="No data",
        show_liquidity_context=True,
        stocks_per_row=1,
        chart_height=2.2,
        row_layout=[("chart", 1.2), ("details", 1.0)],
    )

    assert cards_calls == [
        {
            "tickers": ["AAPL", "MSFT"],
            "selected_universe": "S&P 500",
            "empty_message": "No data",
            "show_liquidity_context": True,
            "stocks_per_row": 1,
            "chart_height": 2.2,
            "row_layout": [("chart", 1.2), ("details", 1.0)],
        }
    ]