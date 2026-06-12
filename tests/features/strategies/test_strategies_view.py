import pandas as pd

from sector_rotation.src.features.strategies import rendering
from sector_rotation.src.features.strategies.view import StrategiesView


class _SessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


def test_strategy_profiles_include_camillo_and_prehn():
    profiles = rendering.get_strategy_profiles()
    names = {profile["name"] for profile in profiles}

    assert "Chris Camillo-Style Social Arbitrage" in names
    assert "Felix Prehn-Style Macro Regime Rotation" in names
    assert all(profile.get("sources") for profile in profiles)
    assert all("guideline" in profile for profile in profiles)


def _make_price_volume_frame(start: float, step: float, periods: int = 260, base_volume: float = 1_000_000.0) -> pd.DataFrame:
    prices = [start + step * i for i in range(periods)]
    volumes = [base_volume] * (periods - 20) + [base_volume * 1.5] * 20
    return pd.DataFrame({"Close": prices, "Volume": volumes})


def test_camillo_agent_returns_pick_table(monkeypatch):
    monkeypatch.setattr(rendering, "get_universe_tickers", lambda universe: ["AAA", "BBB", "CCC"])
    monkeypatch.setattr(rendering, "get_universe_stock_name", lambda universe, ticker: f"Name-{ticker}")

    frames = {
        "AAA": _make_price_volume_frame(10.0, 0.30),
        "BBB": _make_price_volume_frame(20.0, 0.12),
        "CCC": _make_price_volume_frame(30.0, -0.02),
    }

    monkeypatch.setattr(rendering, "fetch_ticker_data_batch", lambda ticker, force_refresh=False: (ticker, frames[ticker]))

    picks = rendering._camillo_social_arbitrage_agent("S&P 500", max_candidates=3, top_n=2)

    assert not picks.empty
    assert list(picks.columns) == [
        "ticker",
        "name",
        "entry_zone",
        "stop_zone",
        "take_profit_1",
        "take_profit_2",
        "risk_pct",
        "mom_1m_pct",
        "mom_3m_pct",
        "volume_ratio_20_60",
        "signal_score",
    ]
    assert len(picks) == 2


def test_prehn_agent_returns_regime_and_picks(monkeypatch):
    monkeypatch.setattr(rendering, "get_universe_tickers", lambda universe: ["AAA", "BBB"])
    monkeypatch.setattr(rendering, "get_universe_stock_name", lambda universe, ticker: f"Name-{ticker}")
    monkeypatch.setattr(
        rendering,
        "load_universe",
        lambda universe: pd.DataFrame(
            {
                "Ticker": ["AAA", "BBB"],
                "Name": ["Name-AAA", "Name-BBB"],
                "Sector": ["Technology", "Utilities"],
                "Industry": ["Software", "Electric Utilities"],
            }
        ),
    )

    frames = {
        "SPY": _make_price_volume_frame(100.0, 0.20),
        "TLT": _make_price_volume_frame(100.0, -0.08),
        "UUP": _make_price_volume_frame(30.0, 0.01),
        "AAA": _make_price_volume_frame(10.0, 0.15),
        "BBB": _make_price_volume_frame(10.0, 0.03),
    }
    monkeypatch.setattr(rendering, "fetch_ticker_data_batch", lambda ticker, force_refresh=False: (ticker, frames[ticker]))

    picks, regime = rendering._prehn_macro_rotation_agent("S&P 500", max_candidates=2, top_n=2)

    assert not picks.empty
    assert regime["regime"] in {"Risk-On", "Defensive / Risk-Off", "USD-Tight / Cautious"}
    assert "entry_zone" in picks.columns
    assert "stop_zone" in picks.columns
    assert "take_profit_1" in picks.columns


def test_strategies_view_sets_view_and_clears_scope(monkeypatch):
    session_state = _SessionState(
        selected_sector="Technology",
        selected_industry="Software",
        selected_stock="MSFT",
        view="sector",
    )

    monkeypatch.setattr("sector_rotation.src.features.strategies.view.st.session_state", session_state)

    selected_universe = StrategiesView().render_nav_controls("S&P 500")

    assert selected_universe == "S&P 500"
    assert session_state["view"] == "strategies"
    assert "selected_sector" not in session_state
    assert "selected_industry" not in session_state
    assert "selected_stock" not in session_state
