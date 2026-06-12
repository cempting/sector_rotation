"""Strategies feature rendering."""

import math

import pandas as pd
import streamlit as st

from ...core.data import (
    fetch_ticker_data_batch,
    get_universe_stock_name,
    get_universe_tickers,
    list_universes,
    load_universe,
)


MAX_AGENT_CANDIDATES = 120


def _to_series(values: pd.Series | pd.DataFrame | None) -> pd.Series:
    if isinstance(values, pd.Series):
        return pd.to_numeric(values, errors="coerce").dropna()
    if isinstance(values, pd.DataFrame):
        if "Close" in values.columns:
            return pd.to_numeric(values["Close"], errors="coerce").dropna()
        if values.shape[1] > 0:
            return pd.to_numeric(values.iloc[:, 0], errors="coerce").dropna()
    return pd.Series(dtype=float)


def _stop_take_profit_levels(entry_price: float, close: pd.Series) -> tuple[float, float, float, float]:
    returns = close.pct_change().dropna().tail(20)
    if returns.empty:
        stop_pct = 6.0
    else:
        # Volatility-scaled stop with floor/ceiling so zones stay practical.
        vol_pct = float(returns.std(ddof=0) * math.sqrt(20) * 100.0)
        stop_pct = min(12.0, max(4.0, vol_pct * 1.2))

    stop_price = entry_price * (1.0 - stop_pct / 100.0)
    take_profit_1 = entry_price * (1.0 + (stop_pct * 1.5) / 100.0)
    take_profit_2 = entry_price * (1.0 + (stop_pct * 3.0) / 100.0)
    return stop_pct, stop_price, take_profit_1, take_profit_2


def _macro_regime_snapshot() -> dict[str, object]:
    _ticker, spy_df = fetch_ticker_data_batch("SPY", force_refresh=False)
    _ticker, tlt_df = fetch_ticker_data_batch("TLT", force_refresh=False)
    _ticker, uup_df = fetch_ticker_data_batch("UUP", force_refresh=False)

    spy = _to_series(spy_df.get("Close") if isinstance(spy_df, pd.DataFrame) else None)
    tlt = _to_series(tlt_df.get("Close") if isinstance(tlt_df, pd.DataFrame) else None)
    uup = _to_series(uup_df.get("Close") if isinstance(uup_df, pd.DataFrame) else None)

    def _pct(series: pd.Series, bars: int) -> float:
        if len(series) < bars:
            return 0.0
        first = float(series.iloc[-bars])
        last = float(series.iloc[-1])
        if first <= 0:
            return 0.0
        return (last / first - 1.0) * 100.0

    spy_3m = _pct(spy, 63)
    tlt_3m = _pct(tlt, 63)
    uup_3m = _pct(uup, 63)

    regime = "Risk-On"
    if spy_3m < 0.0 or tlt_3m > 0.0:
        regime = "Defensive / Risk-Off"
    if uup_3m > 3.0 and spy_3m <= 0.0:
        regime = "USD-Tight / Cautious"

    return {
        "regime": regime,
        "spy_3m_pct": spy_3m,
        "tlt_3m_pct": tlt_3m,
        "uup_3m_pct": uup_3m,
    }


def _camillo_social_arbitrage_agent(universe: str, max_candidates: int = MAX_AGENT_CANDIDATES, top_n: int = 8) -> pd.DataFrame:
    tickers = get_universe_tickers(universe)[:max_candidates]
    rows: list[dict[str, object]] = []

    for ticker in tickers:
        _symbol, df = fetch_ticker_data_batch(ticker, force_refresh=False)
        if df is None or df.empty or "Close" not in df.columns or "Volume" not in df.columns:
            continue

        close = _to_series(df["Close"])
        volume = _to_series(df["Volume"])
        if len(close) < 120 or len(volume) < 80:
            continue

        price = float(close.iloc[-1])
        ma50 = float(close.tail(50).mean())
        ma200 = float(close.tail(200).mean()) if len(close) >= 200 else float(close.mean())
        mom_1m = (price / float(close.iloc[-21]) - 1.0) * 100.0
        mom_3m = (price / float(close.iloc[-63]) - 1.0) * 100.0
        vol_ratio = float(volume.tail(20).mean() / max(1.0, volume.tail(80).head(60).mean()))
        high_52w = float(close.tail(252).max()) if len(close) >= 252 else float(close.max())
        near_high = price / max(1e-9, high_52w)
        trend_ok = price > ma50 > ma200

        score = mom_3m + mom_1m * 0.6 + (vol_ratio - 1.0) * 35.0 + (near_high - 0.85) * 80.0 + (5.0 if trend_ok else -3.0)
        stop_pct, stop_price, take_profit_1, take_profit_2 = _stop_take_profit_levels(price, close)

        rows.append(
            {
                "ticker": ticker,
                "name": get_universe_stock_name(universe, ticker),
                "entry_zone": f"{price * 0.99:.2f} - {price * 1.01:.2f}",
                "stop_zone": f"{stop_price * 0.99:.2f} - {stop_price * 1.01:.2f}",
                "take_profit_1": round(take_profit_1, 2),
                "take_profit_2": round(take_profit_2, 2),
                "risk_pct": round(stop_pct, 2),
                "mom_1m_pct": round(mom_1m, 2),
                "mom_3m_pct": round(mom_3m, 2),
                "volume_ratio_20_60": round(vol_ratio, 2),
                "signal_score": round(score, 2),
            }
        )

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values("signal_score", ascending=False).head(top_n).reset_index(drop=True)


def _prehn_macro_rotation_agent(universe: str, max_candidates: int = MAX_AGENT_CANDIDATES, top_n: int = 8) -> tuple[pd.DataFrame, dict[str, object]]:
    regime = _macro_regime_snapshot()
    universe_df = load_universe(universe)
    tickers = get_universe_tickers(universe)[:max_candidates]

    risk_on_sectors = {"Technology", "Communication Services", "Consumer Cyclical", "Consumer Discretionary", "Industrials"}
    defensive_sectors = {"Utilities", "Healthcare", "Health Care", "Consumer Defensive", "Consumer Staples"}

    rows: list[dict[str, object]] = []
    for ticker in tickers:
        _symbol, df = fetch_ticker_data_batch(ticker, force_refresh=False)
        if df is None or df.empty or "Close" not in df.columns:
            continue

        close = _to_series(df["Close"])
        if len(close) < 130:
            continue

        price = float(close.iloc[-1])
        ma20 = float(close.tail(20).mean())
        ma100 = float(close.tail(100).mean())
        trend_3m = (price / float(close.iloc[-63]) - 1.0) * 100.0
        trend_6m = (price / float(close.iloc[-126]) - 1.0) * 100.0
        vol_3m = float(close.pct_change().dropna().tail(63).std(ddof=0) * math.sqrt(252) * 100.0)

        sector = ""
        if not universe_df.empty:
            row = universe_df.loc[universe_df["Ticker"] == ticker]
            if not row.empty:
                sector = str(row.iloc[0]["Sector"])

        sector_bonus = 0.0
        if regime["regime"] == "Risk-On" and sector in risk_on_sectors:
            sector_bonus = 7.0
        elif regime["regime"] != "Risk-On" and sector in defensive_sectors:
            sector_bonus = 7.0

        score = trend_6m * 0.8 + trend_3m * 0.5 - vol_3m * 0.15 + sector_bonus + (2.0 if price > ma20 > ma100 else -2.0)
        stop_pct, stop_price, take_profit_1, take_profit_2 = _stop_take_profit_levels(price, close)

        rows.append(
            {
                "ticker": ticker,
                "name": get_universe_stock_name(universe, ticker),
                "sector": sector,
                "entry_zone": f"{price * 0.995:.2f} - {price * 1.01:.2f}",
                "stop_zone": f"{stop_price * 0.99:.2f} - {stop_price * 1.01:.2f}",
                "take_profit_1": round(take_profit_1, 2),
                "take_profit_2": round(take_profit_2, 2),
                "risk_pct": round(stop_pct, 2),
                "trend_3m_pct": round(trend_3m, 2),
                "trend_6m_pct": round(trend_6m, 2),
                "ann_vol_pct": round(vol_3m, 2),
                "signal_score": round(score, 2),
            }
        )

    if not rows:
        return pd.DataFrame(), regime

    picks = pd.DataFrame(rows).sort_values("signal_score", ascending=False).head(top_n).reset_index(drop=True)
    return picks, regime


def get_strategy_profiles() -> list[dict[str, object]]:
    """Return strategy profiles inspired by public investor/trader playbooks."""
    return [
        {
            "name": "Chris Camillo-Style Social Arbitrage",
            "style": "Trend and behavior-driven equity idea generation",
            "time_horizon": "Weeks to quarters",
            "primary_edge": "Spot consumer behavior shifts before Wall Street prices them",
            "signals": [
                "Search and social trend acceleration (Google Trends, Reddit, X, TikTok)",
                "Rising attention around products/services before earnings inflection",
                "Cross-platform confirmation that trend is persistent, not just viral noise",
            ],
            "execution": [
                "Start from real-world/social signal, then map to listed beneficiaries",
                "Validate with at least two independent data lenses before sizing",
                "Enter before consensus, scale out as thesis becomes mainstream",
            ],
            "guideline": {
                "pick_flow": [
                    "Screen for price + volume expansion and strong 1M/3M momentum",
                    "Prefer names near 52-week highs with healthy trend structure",
                    "Reject noisy spikes that fail cross-validation across signals",
                ],
                "entry_rule": "Buy in the entry zone when price closes above 20-day average and volume ratio is > 1.2.",
                "stop_rule": "Set stop below volatility-adjusted invalidation zone (about 4-12% depending on volatility).",
                "take_profit_rule": "Scale out 50% at TP1 (about 1.5R), trail remainder toward TP2 (about 3R).",
                "position_sizing": "Risk per idea: 0.5% to 1.0% of portfolio equity.",
            },
            "risk_controls": [
                "Avoid over-crowded late-stage trends",
                "Use predefined invalidation points and maximum position caps",
                "Treat every trend thesis as probabilistic, not certain",
            ],
            "sources": [
                {
                    "label": "Social Arbitrage article (TickerTrends)",
                    "url": "https://blog.tickertrends.io/p/social-arbitrage-investing-chris-camillo",
                },
            ],
        },
        {
            "name": "Felix Prehn-Style Macro Regime Rotation",
            "style": "Top-down macro + risk-on/risk-off portfolio rotation",
            "time_horizon": "Swing to multi-month",
            "primary_edge": "Align exposure with macro regime shifts and liquidity cycles",
            "signals": [
                "Rate/central-bank direction and real-yield trends",
                "Intermarket leadership (equities, bonds, commodities, USD)",
                "Breadth and trend health across risk assets",
            ],
            "execution": [
                "Define current regime first: expansion, slowdown, or stress",
                "Tilt toward assets/styles favored by that regime",
                "Rebalance when regime evidence changes, not on headlines alone",
            ],
            "guideline": {
                "pick_flow": [
                    "Identify macro regime from SPY/TLT/USD trend mix",
                    "In risk-on regimes, prefer offensive sectors with clean uptrends",
                    "In defensive regimes, prioritize lower-beta sectors with stable trend",
                ],
                "entry_rule": "Enter in pullback-to-trend zones while 20-day average remains above 100-day average.",
                "stop_rule": "Stop below regime invalidation level or swing low, capped by volatility-adjusted risk.",
                "take_profit_rule": "Take partial profit near 1.5R and rebalance remainder around regime shift or 3R.",
                "position_sizing": "Risk per idea: 0.4% to 0.8% of portfolio equity.",
            },
            "risk_controls": [
                "Keep gross/net exposure aligned to volatility regime",
                "Use scenario planning and hard portfolio drawdown limits",
                "Diversify by drivers, not just by ticker count",
            ],
            "sources": [
                {
                    "label": "Felix Prehn public content",
                    "url": "https://www.goatacademy.co.uk/",
                },
            ],
        },
    ]


def _render_strategy_card(profile: dict[str, object]) -> None:
    st.markdown(f"### {profile['name']}")
    st.caption(f"Style: {profile['style']} | Horizon: {profile['time_horizon']}")
    st.markdown(f"**Primary edge:** {profile['primary_edge']}")
    guideline = profile["guideline"]
    summary_lines = [
        f"- Pick flow: {guideline['pick_flow'][0]}",
        f"- Entry: {guideline['entry_rule']}",
        f"- Stop: {guideline['stop_rule']}",
        f"- Take profit: {guideline['take_profit_rule']}",
    ]
    st.markdown("\n".join(summary_lines))

    with st.expander("Playbook details", expanded=False):
        st.markdown("**Signal stack**")
        for signal in profile["signals"]:
            st.markdown(f"- {signal}")

        st.markdown("**Execution framework**")
        for step in profile["execution"]:
            st.markdown(f"- {step}")

        st.markdown("**Stock selection guideline**")
        for step in guideline["pick_flow"]:
            st.markdown(f"- {step}")

        st.markdown("**Risk controls**")
        for risk_rule in profile["risk_controls"]:
            st.markdown(f"- {risk_rule}")

        st.markdown(f"**Position sizing:** {guideline['position_sizing']}")
        source_links = [f"[{src['label']}]({src['url']})" for src in profile["sources"]]
        st.markdown("**Sources:** " + " | ".join(source_links))


def render_strategies_view() -> None:
    """Render strategy playbooks inspired by public investors/traders."""
    st.subheader("Strategies")
    st.caption(
        "Educational strategy playbooks inspired by public investor/trader frameworks. "
        "Use these as research templates, not as direct investment advice."
    )

    profiles = get_strategy_profiles()
    names = [str(profile["name"]) for profile in profiles]
    universes = list_universes()

    top_left, top_mid = st.columns([3, 2])
    with top_left:
        selected = st.selectbox("Strategy", names, key="strategies_selected_name")
    with top_mid:
        selected_universe = st.selectbox(
            "Universe",
            universes,
            index=universes.index(st.session_state.get("selected_universe", universes[0])) if universes else 0,
            key="strategies_universe",
        )

    selected_profile = next(profile for profile in profiles if profile["name"] == selected)
    overview_tab, picks_tab = st.tabs(["Strategy overview", "Strategy agent picks"])

    with overview_tab:
        _render_strategy_card(selected_profile)

        with st.expander("Universal pre-trade checklist", expanded=False):
            st.markdown("- Thesis: what is the edge and what would disprove it?")
            st.markdown("- Timing: what catalyst window are you trading?")
            st.markdown("- Sizing: max position size and max portfolio heat")
            st.markdown("- Risk: stop/hedge plan and expected drawdown")
            st.markdown("- Exit: target, trailing logic, and time-based stop")

    with picks_tab:
        st.caption(
            "Each strategy agent applies its own style-specific scoring model and returns candidate picks with "
            "entry, stop, and take-profit zones."
        )

        settings_open = st.toggle("Show agent settings", value=False, key="strategies_show_agent_settings")
        if settings_open:
            with st.popover("Agent settings", use_container_width=False):
                agent_col_left, agent_col_right = st.columns([2, 2])
                with agent_col_left:
                    max_candidates = st.slider(
                        "Scan depth",
                        min_value=30,
                        max_value=200,
                        value=MAX_AGENT_CANDIDATES,
                        step=10,
                        key="strategies_agent_scan_depth",
                    )
                with agent_col_right:
                    top_n = st.slider(
                        "Number of picks",
                        min_value=3,
                        max_value=15,
                        value=8,
                        step=1,
                        key="strategies_agent_top_n",
                    )
                st.markdown("- Run the selected strategy agent to populate pick candidates.")
                st.markdown("- Increase scan depth only if the universe is broad and you need more candidates.")
        else:
            max_candidates = int(st.session_state.get("strategies_agent_scan_depth", MAX_AGENT_CANDIDATES))
            top_n = int(st.session_state.get("strategies_agent_top_n", 8))

        if st.button("Run Strategy Agent", key="strategies_run_agent", use_container_width=False):
            if selected == "Chris Camillo-Style Social Arbitrage":
                picks = _camillo_social_arbitrage_agent(selected_universe, max_candidates=max_candidates, top_n=top_n)
                regime = None
            else:
                picks, regime = _prehn_macro_rotation_agent(selected_universe, max_candidates=max_candidates, top_n=top_n)

            if regime is not None:
                st.caption(
                    f"Macro regime: {regime['regime']} | SPY 3M: {regime['spy_3m_pct']:.2f}% | "
                    f"TLT 3M: {regime['tlt_3m_pct']:.2f}% | UUP 3M: {regime['uup_3m_pct']:.2f}%"
                )

            if picks.empty:
                st.info("No picks found for the current filters/universe. Try increasing scan depth or changing universe.")
            else:
                top_picks = picks.head(3)
                st.markdown("#### Top picks")
                st.dataframe(
                    top_picks,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "take_profit_1": st.column_config.NumberColumn("TP1", format="%.2f"),
                        "take_profit_2": st.column_config.NumberColumn("TP2", format="%.2f"),
                        "risk_pct": st.column_config.NumberColumn("Risk %", format="%.2f"),
                        "signal_score": st.column_config.NumberColumn("Signal score", format="%.2f"),
                    },
                )
                if len(picks) > 3:
                    with st.expander(f"Show remaining {len(picks) - 3} picks", expanded=False):
                        st.dataframe(
                            picks.iloc[3:],
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "take_profit_1": st.column_config.NumberColumn("TP1", format="%.2f"),
                                "take_profit_2": st.column_config.NumberColumn("TP2", format="%.2f"),
                                "risk_pct": st.column_config.NumberColumn("Risk %", format="%.2f"),
                                "signal_score": st.column_config.NumberColumn("Signal score", format="%.2f"),
                            },
                        )
