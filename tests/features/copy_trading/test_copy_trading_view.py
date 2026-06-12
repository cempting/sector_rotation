from datetime import date

import pandas as pd

from sector_rotation.src.features.copy_trading import rendering
from sector_rotation.src.features.copy_trading.view import CopyTradingView


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def test_get_copy_trading_activity_has_required_columns(monkeypatch):
    monkeypatch.setattr(rendering, "_fetch_sec_13f_activities", lambda: pd.DataFrame())
    monkeypatch.setattr(rendering, "_fetch_congress_activities", lambda: pd.DataFrame())
    activities = rendering.get_copy_trading_activity(today=date(2026, 5, 25))

    assert not activities.empty
    assert list(activities.columns) == [
        "actor",
        "actor_type",
        "ticker",
        "action",
        "reported_on",
        "source",
        "source_url",
        "notes",
    ]


def test_filter_copy_trading_activity_filters_by_type_and_query(monkeypatch):
    monkeypatch.setattr(rendering, "_fetch_sec_13f_activities", lambda: pd.DataFrame())
    monkeypatch.setattr(rendering, "_fetch_congress_activities", lambda: pd.DataFrame())
    activities = rendering.get_copy_trading_activity(today=date.today())

    filtered = rendering.filter_copy_trading_activity(
        activities,
        actor_types=["US Politician (Public filings)"],
        lookback_days=120,
        query="nvda",
    )

    assert not filtered.empty
    assert (filtered["actor_type"] == "US Politician (Public filings)").all()
    assert (filtered["ticker"] == "NVDA").any()


def test_copy_trading_activity_keeps_politician_rows_when_only_sec_live(monkeypatch):
    sec_live = pd.DataFrame(
        {
            "actor": ["Berkshire Hathaway"],
            "actor_type": ["Fund"],
            "ticker": [""],
            "action": ["13F-HR"],
            "reported_on": [date.today()],
            "source": ["SEC EDGAR"],
            "source_url": ["https://www.sec.gov/"],
            "notes": ["Live SEC filing"],
        }
    )

    monkeypatch.setattr(rendering, "_fetch_sec_13f_activities", lambda: sec_live)
    monkeypatch.setattr(rendering, "_fetch_congress_activities", lambda: pd.DataFrame())

    activities = rendering.get_copy_trading_activity(today=date.today())

    assert (activities["actor"] == "Nancy Pelosi").any()
    assert (activities["source"] == "SEC EDGAR").any()


def test_watchlist_alerts_detect_recent_matches():
    activities = pd.DataFrame(
        {
            "actor": ["A", "B"],
            "actor_type": ["Fund", "Fund"],
            "ticker": ["MSFT", "AAPL"],
            "action": ["Buy", "Sell"],
            "reported_on": [date.today(), date.today()],
            "source": ["SEC", "SEC"],
            "source_url": ["https://example.com/1", "https://example.com/2"],
            "notes": ["n1", "n2"],
        }
    )

    count, rows = rendering._watchlist_alerts(activities, ["MSFT"], 30)

    assert count == 1
    assert len(rows) == 1
    assert rows.iloc[0]["ticker"] == "MSFT"


def test_copy_trading_view_sets_view_and_clears_scope(monkeypatch):
    session_state = _SessionState(
        selected_sector="Technology",
        selected_industry="Software",
        selected_stock="MSFT",
        view="sector",
    )
    monkeypatch.setattr("sector_rotation.src.features.copy_trading.view.st.session_state", session_state)

    selected_universe = CopyTradingView().render_nav_controls("S&P 500")

    assert selected_universe == "S&P 500"
    assert session_state["view"] == "CopyTrading"
    assert "selected_sector" not in session_state
    assert "selected_industry" not in session_state
    assert "selected_stock" not in session_state
