import pandas as pd

from sector_rotation.src.core.ui import dedicated_stock_view
from sector_rotation.src.core.ui import stock_cards


class _ContextStub:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_render_stock_cards_focus_mode_uses_full_detail_layout(monkeypatch):
    session_state = {
        "details_focus_universe": "S&P 500",
        "details_focus_ticker": "MSFT",
        "details_opening_ticker": "MSFT",
    }
    chart_calls = []
    detail_calls = []
    macro_calls = []
    recent_calls = []

    df = pd.DataFrame(
        {
            "Close": [100.0, 101.0, 102.0, 103.0],
            "Volume": [1_000_000, 1_100_000, 1_050_000, 1_250_000],
        }
    )

    def fake_columns(spec):
        count = spec if isinstance(spec, int) else len(spec)
        return [_ContextStub() for _ in range(count)]

    monkeypatch.setattr(stock_cards.st, "session_state", session_state)
    monkeypatch.setattr(stock_cards.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(stock_cards.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(stock_cards.st, "columns", fake_columns)
    monkeypatch.setattr(stock_cards.st, "spinner", lambda *args, **kwargs: _ContextStub())
    monkeypatch.setattr(stock_cards.st, "button", lambda *args, **kwargs: False)
    monkeypatch.setattr(stock_cards.st, "rerun", lambda: None)
    monkeypatch.setattr(
        stock_cards,
        "fetch_market_data_with_status",
        lambda *args, **kwargs: ({"MSFT": df}, {"MSFT": {"label": "Live (up to date)"}}),
    )
    monkeypatch.setattr(stock_cards, "get_universe_stock_name", lambda universe, ticker: "Microsoft")
    monkeypatch.setattr(stock_cards, "render_stock_chart", lambda frame, ticker, figsize: chart_calls.append(figsize))

    stock_cards.render_stock_cards(
        tickers=["MSFT", "AAPL"],
        selected_universe="S&P 500",
        empty_message="Empty",
        show_liquidity_context=True,
        stocks_per_row=1,
        chart_height=2.2,
        row_layout=[("chart", 1.2), ("details", 1.0), ("macro", 0.9)],
        compute_stock_metrics=lambda frame, ticker: {"latest": 103.0, "Volume": 1_250_000},
        stock_classification=lambda universe, ticker: {"sector": "Technology", "industry": "Software"},
        macro_impact_snapshot=lambda ticker: {"macro_context": "Supportive"},
        recent_info_snapshot=lambda universe, ticker: {"news_items": [{"title": "Headline", "topic": "General", "provider": "Wire"}]},
        render_stock_details_panel=lambda *args, **kwargs: detail_calls.append(kwargs),
        render_macro_context_card=lambda *args, **kwargs: macro_calls.append(kwargs),
        render_recent_information_card=lambda recent: recent_calls.append(recent),
    )

    assert len(chart_calls) == 1
    assert chart_calls[0][0] == dedicated_stock_view.DEDICATED_CHART_WIDTH
    assert chart_calls[0][1] == dedicated_stock_view.DEDICATED_CHART_MIN_HEIGHT
    # dedicated view calls details panel twice: once for "header", once for "body"
    assert len(detail_calls) == 2
    sections = {c["detail_section"] for c in detail_calls}
    assert sections == {"header", "body"}
    assert all(c["show_full_details"] is True for c in detail_calls)
    assert len(macro_calls) == 1
    assert len(recent_calls) == 1
    assert "details_opening_ticker" not in session_state