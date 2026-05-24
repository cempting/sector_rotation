"""Shared rendering primitives consumed by feature modules."""

from collections.abc import Callable

import pandas as pd
import streamlit as st
import yfinance as yf

from ...charts import get_trend_colors, render_chart
from ...core.data.favorites import is_favorite, toggle_favorite
from ...core.analytics import stock_analytics
from . import stock_cards
from .view_components import (
    render_macro_context_card,
    render_recent_information_card,
    render_stock_details_panel,
)


def compute_return_vol_rr(close: pd.Series, lookback: int = 30) -> dict[str, float]:
    return stock_analytics.compute_return_vol_rr(close, lookback=lookback)


def render_data_card(
    title: str,
    close: pd.Series,
    volume: pd.Series,
    subtitle: str = "",
    metadata: str = "",
    chart_params: dict | None = None,
    nav_action: Callable[[], None] | None = None,
) -> None:
    st.subheader(title)
    if subtitle:
        st.write(subtitle)
    if metadata:
        st.write(metadata)

    if close.empty:
        st.write("No data available.")
        return

    ma50 = close.rolling(50).mean()
    bg_color, bar_color = get_trend_colors(ma50)
    params = chart_params or {"y_label": "Price", "legend_label": "Price", "figsize": (5, 3)}
    render_chart(close, volume, ma50, bg_color, bar_color, **params)

    if nav_action:
        nav_action()


def _compute_stock_metrics(df: pd.DataFrame, ticker: str) -> dict:
    return stock_analytics.compute_stock_metrics(df, ticker, ticker_factory=yf.Ticker)


@st.cache_data(ttl=900, show_spinner=False)
def _macro_impact_snapshot(ticker: str) -> dict[str, str | float]:
    return stock_analytics.macro_impact_snapshot(ticker)


@st.cache_data(ttl=900, show_spinner=False)
def _recent_info_snapshot(universe: str, ticker: str) -> dict[str, object]:
    return stock_analytics.recent_info_snapshot(universe, ticker, ticker_factory=yf.Ticker)


@st.cache_data(ttl=3600, show_spinner=False)
def _stock_classification(universe: str, ticker: str) -> dict[str, str]:
    return stock_analytics.stock_classification(universe, ticker)


def _toggle_favorite(universe: str, ticker: str) -> None:
    now_favorite = toggle_favorite(universe, ticker)
    if now_favorite:
        st.toast(f"Added {ticker} to favorites ({universe})")
    else:
        st.toast(f"Removed {ticker} from favorites ({universe})")


def _render_stock_details_panel(
    metrics: dict,
    company_name: str,
    ticker: str,
    universe: str,
    sector: str = "N/A",
    industry: str = "N/A",
    show_liquidity_context: bool = False,
    show_full_details: bool = False,
    detail_section: str = "full",
) -> None:
    is_now_favorite = is_favorite(universe, ticker)
    favorite_label = "★" if is_now_favorite else "☆"
    render_stock_details_panel(
        metrics=metrics,
        company_name=company_name,
        ticker=ticker,
        universe=universe,
        sector=sector,
        industry=industry,
        show_liquidity_context=show_liquidity_context,
        show_full_details=show_full_details,
        favorite_label=favorite_label,
        favorite_button_key=f"favorite-{universe}-{ticker}",
        on_toggle=_toggle_favorite,
        on_toggle_args=(universe, ticker),
        detail_section=detail_section,
    )


def render_stock_cards(
    tickers: list[str],
    selected_universe: str,
    empty_message: str,
    show_liquidity_context: bool = False,
    stocks_per_row: int = 2,
    chart_height: float | None = None,
    row_layout: list[tuple[str, float]] | None = None,
) -> None:
    stock_cards.render_stock_cards(
        tickers=tickers,
        selected_universe=selected_universe,
        empty_message=empty_message,
        show_liquidity_context=show_liquidity_context,
        stocks_per_row=stocks_per_row,
        chart_height=chart_height,
        row_layout=row_layout,
        compute_stock_metrics=_compute_stock_metrics,
        stock_classification=_stock_classification,
        macro_impact_snapshot=_macro_impact_snapshot,
        recent_info_snapshot=_recent_info_snapshot,
        render_stock_details_panel=_render_stock_details_panel,
        render_macro_context_card=render_macro_context_card,
        render_recent_information_card=render_recent_information_card,
    )


__all__ = ["compute_return_vol_rr", "render_data_card", "render_stock_cards"]
