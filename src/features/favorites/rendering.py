"""Favorites feature rendering."""

import streamlit as st
import yfinance as yf

from ...core.analytics import stock_analytics
from ...core.data import fetch_ticker_data_batch, get_universe_stock_name, list_all_favorites
from ...core.ui import FAVORITES_CHART_HEIGHT, FAVORITES_ROW_LAYOUT, render_stock_cards


FAVORITES_COMPACT_ROW_LAYOUT = [
    ("chart", 1.2),
    ("details", 1.0),
    ("macro", 0.9),
]
FAVORITES_COMPACT_CHART_HEIGHT = 4.4


def _safe_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _band_score(value: float | None, good: float, weak: float, higher_is_better: bool = True) -> int:
    if value is None:
        return 50
    if higher_is_better:
        if value >= good:
            return 100
        if value <= weak:
            return 25
        return 60
    if value <= good:
        return 100
    if value >= weak:
        return 25
    return 60


def _build_compact_scores(metrics: dict[str, object]) -> dict[str, int]:
    sales_yoy = _safe_float(metrics.get("revenue_growth_yoy"))
    eps_yoy = _safe_float(metrics.get("earnings_growth_yoy"))
    gross_margin = _safe_float(metrics.get("gross_margin"))
    operating_margin = _safe_float(metrics.get("operating_margin"))
    roce = _safe_float(metrics.get("roce"))
    fcf_margin = _safe_float(metrics.get("fcf_margin"))
    fcf_yield = _safe_float(metrics.get("fcf_yield"))
    risk_reward = _safe_float(metrics.get("risk_reward"))
    vol_20d = _safe_float(metrics.get("volatility_20d"))

    quality = (
        _band_score(gross_margin, good=30, weak=12)
        + _band_score(operating_margin, good=16, weak=5)
        + _band_score(roce, good=15, weak=7)
    ) / 3
    growth = (
        _band_score(sales_yoy * 100 if sales_yoy is not None else None, good=10, weak=0)
        + _band_score(eps_yoy * 100 if eps_yoy is not None else None, good=12, weak=0)
    ) / 2
    cashflow = (
        _band_score(fcf_margin, good=10, weak=2)
        + _band_score(fcf_yield, good=4, weak=1.5)
    ) / 2
    risk = (
        _band_score(risk_reward, good=0.7, weak=0.2)
        + _band_score(vol_20d, good=2.0, weak=4.5, higher_is_better=False)
    ) / 2
    composite = (quality + growth + cashflow + risk) / 4

    return {
        "quality": int(round(quality)),
        "growth": int(round(growth)),
        "cashflow": int(round(cashflow)),
        "risk": int(round(risk)),
        "composite": int(round(composite)),
    }


@st.cache_data(ttl=900, show_spinner=False)
def _compact_score_snapshot(universe: str, ticker: str) -> dict[str, int]:
    _meta, df = fetch_ticker_data_batch(ticker, False)
    if df.empty:
        return {"quality": 50, "growth": 50, "cashflow": 50, "risk": 50, "composite": 50}
    metrics = stock_analytics.compute_stock_metrics(df, ticker, ticker_factory=yf.Ticker)
    return _build_compact_scores(metrics)


def _render_score_chip(label: str, score: int) -> None:
    color = "#4ecb71" if score >= 75 else "#f2c94c" if score >= 45 else "#ff6b6b"
    st.markdown(
        (
            '<div style="margin-bottom:0.2rem;">'
            f'<div style="font-size:0.62rem; opacity:0.75;">{label} <span style="float:right;">{score}</span></div>'
            '<div style="height:0.28rem; background:rgba(255,255,255,0.08); border-radius:999px; overflow:hidden;">'
            f'<div style="height:100%; width:{score}%; background:{color}; border-radius:999px;"></div>'
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_compact_card(universe: str, ticker: str) -> None:
    company_name = get_universe_stock_name(universe, ticker)
    scores = _compact_score_snapshot(universe, ticker)
    st.markdown(
        (
            '<div style="border:1px solid rgba(128,128,128,0.25); border-radius:0.6rem; '
            'padding:0.35rem 0.4rem; margin-bottom:0.35rem; background:rgba(255,255,255,0.02);">'
            f'<div style="font-size:0.64rem; opacity:0.75;">{universe}</div>'
            f'<div style="font-size:0.82rem; font-weight:700; margin-bottom:0.18rem;">{company_name} ({ticker})</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    _render_score_chip("Composite", scores["composite"])
    _render_score_chip("Quality", scores["quality"])
    _render_score_chip("Growth", scores["growth"])
    _render_score_chip("Cash Flow", scores["cashflow"])
    _render_score_chip("Risk", scores["risk"])

    st.markdown('<div class="favorites-open-primary">', unsafe_allow_html=True)
    if st.button("Open Full Analysis", key=f"favorites-open-{universe}-{ticker}", use_container_width=True):
        st.session_state["favorites_focus_universe"] = universe
        st.session_state["favorites_focus_ticker"] = ticker
        st.session_state["details_opening_ticker"] = ticker
        st.session_state["details_focus_universe"] = universe
        st.session_state["details_focus_ticker"] = ticker
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def _render_dedicated_stock_view(
    focused_universe: str,
    focused_ticker: str,
    render_stock_cards_fn,
) -> None:
    nav_col, title_col = st.columns([1, 7])
    with nav_col:
        if st.button("Back", key="favorites-dedicated-back", use_container_width=True):
            st.session_state.pop("favorites_focus_universe", None)
            st.session_state.pop("favorites_focus_ticker", None)
            st.session_state.pop("details_focus_universe", None)
            st.session_state.pop("details_focus_ticker", None)
            st.rerun()
    with title_col:
        st.subheader("Favorites · Dedicated Stock View")
        st.caption(f"{focused_universe} · {focused_ticker}")

    render_stock_cards_fn(
        tickers=[focused_ticker],
        selected_universe=focused_universe,
        empty_message="Ticker could not be loaded.",
        show_liquidity_context=True,
        stocks_per_row=1,
        chart_height=FAVORITES_CHART_HEIGHT,
        row_layout=FAVORITES_ROW_LAYOUT,
    )


def render_favorites_page(
    render_stock_cards_fn=None,
    compact_mode: bool = False,
    focused_universe: str | None = None,
    focused_ticker: str | None = None,
) -> None:
    render_stock_cards_fn = render_stock_cards_fn or render_stock_cards
    global_focus_universe = st.session_state.get("details_focus_universe")
    global_focus_ticker = st.session_state.get("details_focus_ticker")

    grouped = list_all_favorites()
    total = sum(len(tickers) for tickers in grouped.values())
    st.markdown(
        """
        <style>
        .favorites-view .sr-workbench {
            padding: 0.3rem 0.34rem;
            border-radius: 0.58rem;
        }
        .favorites-view .sr-hero {
            margin-bottom: 0.2rem;
            padding: 0.24rem 0.28rem;
        }
        .favorites-view .sr-hero-grid {
            gap: 0.14rem;
        }
        .favorites-view .sr-pane {
            margin-bottom: 0.16rem;
            padding: 0.22rem 0.24rem;
        }
        .favorites-view .sr-details-card {
            margin-bottom: 0.12rem;
            min-height: 1.78rem;
            padding: 0.16rem 0.24rem;
        }
        .favorites-view .sr-details-value {
            font-size: 0.9rem;
        }
        .favorites-view .sr-details-explain {
            font-size: 0.52rem;
            line-height: 1.08;
        }
        .favorites-view .favorites-open-primary button {
            border: 1px solid rgba(78, 203, 113, 0.55) !important;
            background: linear-gradient(180deg, rgba(78,203,113,0.22), rgba(78,203,113,0.1)) !important;
            font-weight: 650 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="favorites-view">', unsafe_allow_html=True)
    st.subheader("Favorites · All Universes")
    st.caption(f"{total} favorite stocks")

    if not grouped:
        st.info("No favorites yet. Open an industry stock page and tap ☆ Favorite.")
        return

    if global_focus_universe and global_focus_ticker:
        _render_dedicated_stock_view(global_focus_universe, global_focus_ticker, render_stock_cards_fn)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    if compact_mode and focused_universe and focused_ticker:
        _render_dedicated_stock_view(focused_universe, focused_ticker, render_stock_cards_fn)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    if compact_mode:
        for universe_name, tickers in grouped.items():
            st.markdown(f"**{universe_name}**")
            cols = st.columns(3)
            for idx, ticker in enumerate(tickers):
                with cols[idx % 3]:
                    _render_compact_card(universe_name, ticker)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    for universe_name, tickers in grouped.items():
        st.markdown(f"**{universe_name}**")
        if len(tickers) <= 1:
            stocks_per_row = 1
        elif len(tickers) <= 4:
            stocks_per_row = 2
        else:
            stocks_per_row = 3
        render_stock_cards_fn(
            tickers=tickers,
            selected_universe=universe_name,
            empty_message="",
            show_liquidity_context=True,
            stocks_per_row=stocks_per_row,
            chart_height=FAVORITES_COMPACT_CHART_HEIGHT,
            row_layout=FAVORITES_COMPACT_ROW_LAYOUT,
        )
    st.markdown('</div>', unsafe_allow_html=True)
