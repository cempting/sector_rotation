import streamlit as st
import pandas as pd
import yfinance as yf
from .charts import get_trend_colors, render_chart
from .data.favorites import is_favorite, toggle_favorite
from .views.view_components import (
    format_fundamental as _format_fundamental_component,
    render_macro_context_card as _render_macro_context_card,
    render_recent_information_card as _render_recent_information_card,
    render_stock_details_panel as _render_stock_details_panel_component,
)
from .logic import stock_analytics
from .logic.app_control import open_industry_stocks as _open_industry_stocks_control
from .views import page_views
from .views import stock_cards


def _compute_return_vol_rr(close: pd.Series, lookback: int = 30) -> dict[str, float]:
    # Keep wrapper name stable for existing tests/imports.
    return stock_analytics.compute_return_vol_rr(close, lookback=lookback)


@st.cache_data(ttl=900, show_spinner=False)
def _macro_impact_snapshot(ticker: str) -> dict[str, str | float]:
    return stock_analytics.macro_impact_snapshot(ticker)


def _news_topic(title: str) -> str:
    return stock_analytics.news_topic(title)


@st.cache_data(ttl=900, show_spinner=False)
def _recent_info_snapshot(universe: str, ticker: str) -> dict[str, object]:
    return stock_analytics.recent_info_snapshot(universe, ticker, ticker_factory=yf.Ticker)


@st.cache_data(ttl=3600, show_spinner=False)
def _stock_classification(universe: str, ticker: str) -> dict[str, str]:
    return stock_analytics.stock_classification(universe, ticker)


def safe_format(val):
    if hasattr(val, "item"):
        val = val.item()
    try:
        return f"{float(val):.2f}" if pd.notna(val) else "N/A"
    except (ValueError, TypeError):
        return "N/A"


def render_data_card(title: str, close: pd.Series, volume: pd.Series,
                      subtitle: str = "", metadata: str = "",
                      chart_params: dict = None, nav_action: callable = None) -> None:
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


def render_dashboard_grid(title: str, items: list, item_fetcher: callable,
                          cols: int = 3, back_nav: bool = False) -> None:
    st.title(title, )

    if not items:
        st.write("No items found.")
        return

    columns = st.columns(cols)
    for i, item in enumerate(items):
        with columns[i % cols]:
            item_fetcher(item)

    if back_nav and st.button("Back"):
        st.session_state.view = "sector"
        st.rerun()


def render_industry_dashboard(sector: str) -> None:
    page_views.render_industry_dashboard(
        sector=sector,
        compute_return_vol_rr=_compute_return_vol_rr,
        render_data_card=render_data_card,
        open_industry_stocks=_open_industry_stocks,
    )


def _open_industry_stocks(sector: str, industry: str) -> None:
    _open_industry_stocks_control(sector, industry)


def _nav_to_industry_stocks(sector: str, industry: str) -> None:
    st.button(
        "View Stocks",
        key=f"stocks-{sector}-{industry}",
        on_click=_open_industry_stocks,
        args=(sector, industry),
    )


def _compute_stock_metrics(df: pd.DataFrame, ticker: str) -> dict:
    # Keep wrapper name stable for existing tests/imports.
    return stock_analytics.compute_stock_metrics(df, ticker, ticker_factory=yf.Ticker)


def _format_fundamental(val, is_pct=False):
    """Compatibility wrapper for tests and existing call-sites."""
    return _format_fundamental_component(val, is_pct=is_pct)


def _render_stock_details_panel(
    metrics: dict,
    company_name: str,
    ticker: str,
    universe: str,
    sector: str = "N/A",
    industry: str = "N/A",
    show_liquidity_context: bool = False,
) -> None:
    """Wrapper that keeps orchestration local while delegating UI rendering."""
    is_now_favorite = is_favorite(universe, ticker)
    favorite_label = "★" if is_now_favorite else "☆"
    _render_stock_details_panel_component(
        metrics=metrics,
        company_name=company_name,
        ticker=ticker,
        sector=sector,
        industry=industry,
        show_liquidity_context=show_liquidity_context,
        favorite_label=favorite_label,
        favorite_button_key=f"favorite-{universe}-{ticker}",
        on_toggle=_toggle_favorite,
        on_toggle_args=(universe, ticker),
    )


def _toggle_favorite(universe: str, ticker: str) -> None:
    now_favorite = toggle_favorite(universe, ticker)
    if now_favorite:
        st.toast(f"Added {ticker} to favorites ({universe})")
    else:
        st.toast(f"Removed {ticker} from favorites ({universe})")


def _render_stock_cards(
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
        render_macro_context_card=_render_macro_context_card,
        render_recent_information_card=_render_recent_information_card,
    )


def render_industry_stock_page(sector: str, industry: str) -> None:
    page_views.render_industry_stock_page(
        sector=sector,
        industry=industry,
        render_stock_cards=_render_stock_cards,
    )


def render_favorites_page() -> None:
    page_views.render_favorites_page(render_stock_cards=_render_stock_cards)


def render_search_results_page() -> None:
    page_views.render_search_results_page(render_stock_cards=_render_stock_cards)


def _render_sector_industry_summary(universe: str, sector: str) -> None:
    page_views.render_sector_industry_summary(universe=universe, sector=sector)


def render_sector_card(name: str, ticker: str) -> None:
    page_views.render_sector_card(name=name, ticker=ticker)
