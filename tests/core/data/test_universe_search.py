import pandas as pd

from sector_rotation.src.core.data import universe


def test_search_universe_stocks_matches_ticker_and_name(monkeypatch):
    df = pd.DataFrame(
        {
            "Ticker": ["AAPL", "MSFT", "GOOG", "AMZN"],
            "Name": ["Apple Inc", "Microsoft Corp", "Alphabet", "Amazon.com Inc"],
            "Sector": ["Technology"] * 4,
            "Industry": ["Software"] * 4,
        }
    )

    monkeypatch.setattr(universe, "load_universe", lambda _: df)

    by_ticker = universe.search_universe_stocks("S&P 500", "aa")
    by_name = universe.search_universe_stocks("S&P 500", "micro")

    assert by_ticker == ["AAPL"]
    assert by_name == ["MSFT"]


def test_search_universe_stocks_matches_sector_and_industry(monkeypatch):
    df = pd.DataFrame(
        {
            "Ticker": ["AAPL", "JNJ", "XOM"],
            "Name": ["Apple Inc", "Johnson & Johnson", "Exxon Mobil"],
            "Sector": ["Technology", "Healthcare", "Energy"],
            "Industry": ["Consumer Electronics", "Pharmaceuticals", "Oil & Gas"],
        }
    )

    monkeypatch.setattr(universe, "load_universe", lambda _: df)

    by_sector = universe.search_universe_stocks("S&P 500", "health")
    by_industry = universe.search_universe_stocks("S&P 500", "oil")

    assert by_sector == ["JNJ"]
    assert by_industry == ["XOM"]


def test_search_universe_stocks_prioritizes_prefix(monkeypatch):
    df = pd.DataFrame(
        {
            "Ticker": ["AABC", "BAAA", "ZZZZ"],
            "Name": ["Alpha", "Beta", "Aaa Holdings"],
            "Sector": ["Technology", "Technology", "Technology"],
            "Industry": ["Software", "Software", "Software"],
        }
    )

    monkeypatch.setattr(universe, "load_universe", lambda _: df)

    results = universe.search_universe_stocks("S&P 500", "aa")

    assert results[0] == "AABC"
    assert "BAAA" in results


def test_get_universe_tickers_deduplicates_preserving_order(monkeypatch):
    df = pd.DataFrame(
        {
            "Ticker": ["SN", "STMN", "SN", "NOVO-B", "STMN"],
            "Name": ["Smith & Nephew", "Straumann", "Smith & Nephew", "Novo Nordisk", "Straumann"],
            "Sector": ["Health Care"] * 5,
            "Industry": ["Health Care"] * 5,
        }
    )

    monkeypatch.setattr(universe, "load_universe", lambda _: df)

    results = universe.get_universe_tickers("STOXX Europe 600", sector="Health Care", industry="Health Care")

    assert results == ["SN", "STMN", "NOVO-B"]


def test_search_all_universes_returns_grouped_matches(monkeypatch):
    dfs = {
        "S&P 500": pd.DataFrame(
            {
                "Ticker": ["AAPL", "MSFT"],
                "Name": ["Apple Inc", "Microsoft Corp"],
                "Sector": ["Technology", "Technology"],
                "Industry": ["Hardware", "Software"],
            }
        ),
        "NASDAQ": pd.DataFrame(
            {
                "Ticker": ["AMZN", "GOOG"],
                "Name": ["Amazon.com Inc", "Alphabet"],
                "Sector": ["Consumer Disc", "Technology"],
                "Industry": ["Internet Retail", "Internet"],
            }
        ),
    }

    monkeypatch.setattr(universe, "list_universes", lambda: ["S&P 500", "NASDAQ"])
    monkeypatch.setattr(universe, "load_universe", lambda name: dfs[name])

    results = universe.search_all_universes("a", per_universe_limit=5, total_limit=10)

    assert any(r["universe"] == "S&P 500" and r["ticker"] == "AAPL" for r in results)
    assert any(r["universe"] == "NASDAQ" and r["ticker"] == "AMZN" for r in results)


def test_search_all_universes_honors_total_limit(monkeypatch):
    df = pd.DataFrame(
        {
            "Ticker": ["AAA", "AAB", "AAC"],
            "Name": ["A One", "A Two", "A Three"],
            "Sector": ["Technology", "Technology", "Technology"],
            "Industry": ["Software", "Software", "Software"],
        }
    )

    monkeypatch.setattr(universe, "list_universes", lambda: ["S&P 500", "NASDAQ"])
    monkeypatch.setattr(universe, "load_universe", lambda _: df)

    results = universe.search_all_universes("a", per_universe_limit=3, total_limit=2)

    assert len(results) == 2
