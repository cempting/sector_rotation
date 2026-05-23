from sector_rotation.src.core.ui import stock_focus


def test_open_and_clear_dedicated_stock_view(monkeypatch):
    session_state = {}

    monkeypatch.setattr(stock_focus.st, "session_state", session_state)

    stock_focus.open_dedicated_stock_view("S&P 500", "MSFT")

    assert session_state[stock_focus.DETAILS_FOCUS_UNIVERSE_KEY] == "S&P 500"
    assert session_state[stock_focus.DETAILS_FOCUS_TICKER_KEY] == "MSFT"
    assert session_state[stock_focus.DETAILS_OPENING_TICKER_KEY] == "MSFT"

    stock_focus.clear_dedicated_stock_view()

    assert stock_focus.DETAILS_FOCUS_UNIVERSE_KEY not in session_state
    assert stock_focus.DETAILS_FOCUS_TICKER_KEY not in session_state
    assert stock_focus.DETAILS_OPENING_TICKER_KEY not in session_state


def test_filter_grouped_for_dedicated_focus_limits_to_matching_universe(monkeypatch):
    session_state = {
        stock_focus.DETAILS_FOCUS_UNIVERSE_KEY: "NASDAQ",
        stock_focus.DETAILS_FOCUS_TICKER_KEY: "NVDA",
    }
    grouped = {
        "S&P 500": ["AAPL", "MSFT"],
        "NASDAQ": ["NVDA", "AMZN"],
    }

    monkeypatch.setattr(stock_focus.st, "session_state", session_state)

    render_groups, focus = stock_focus.filter_grouped_for_dedicated_focus(grouped, lambda ticker: ticker)

    assert focus.active is True
    assert render_groups == {"NASDAQ": ["NVDA", "AMZN"]}


def test_filter_grouped_for_dedicated_focus_keeps_all_groups_when_ticker_missing(monkeypatch):
    session_state = {
        stock_focus.DETAILS_FOCUS_UNIVERSE_KEY: "NASDAQ",
        stock_focus.DETAILS_FOCUS_TICKER_KEY: "META",
    }
    grouped = {
        "S&P 500": ["AAPL", "MSFT"],
        "NASDAQ": ["NVDA", "AMZN"],
    }

    monkeypatch.setattr(stock_focus.st, "session_state", session_state)

    render_groups, focus = stock_focus.filter_grouped_for_dedicated_focus(grouped, lambda ticker: ticker)

    assert focus.active is True
    assert render_groups == grouped


def test_prepare_grouped_stock_focus_returns_caption_when_narrowed(monkeypatch):
    session_state = {
        stock_focus.DETAILS_FOCUS_UNIVERSE_KEY: "NASDAQ",
        stock_focus.DETAILS_FOCUS_TICKER_KEY: "NVDA",
    }
    grouped = {
        "S&P 500": ["AAPL", "MSFT"],
        "NASDAQ": ["NVDA", "AMZN"],
    }

    monkeypatch.setattr(stock_focus.st, "session_state", session_state)

    context = stock_focus.prepare_grouped_stock_focus(grouped, lambda ticker: ticker, "Focused test view")

    assert context.narrowed is True
    assert context.caption == "Focused test view · NVDA · NASDAQ"
    assert context.render_groups == {"NASDAQ": ["NVDA", "AMZN"]}