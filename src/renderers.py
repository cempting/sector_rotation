import streamlit as st
import pandas as pd
import yfinance as yf
from .charts import get_trend_colors, render_chart
from .core.ui.view_components import (
    format_fundamental as _format_fundamental_component,
)
from .core.analytics import stock_analytics
from .core.ui.shared_rendering import render_stock_cards as _shared_render_stock_cards


def _compute_return_vol_rr(close: pd.Series, lookback: int = 30) -> dict[str, float]:
    # Keep wrapper name stable for existing tests/imports.
    return stock_analytics.compute_return_vol_rr(close, lookback=lookback)


def _news_topic(title: str) -> str:
    return stock_analytics.news_topic(title)


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
    from .features.sector_industry_stocks.rendering import render_industry_dashboard as render_feature_page
    from .core.analytics.app_control import open_industry_stocks

    render_feature_page(
        sector=sector,
        compute_return_vol_rr=_compute_return_vol_rr,
        render_data_card_fn=render_data_card,
        open_industry_stocks_fn=open_industry_stocks,
    )


def _compute_stock_metrics(df: pd.DataFrame, ticker: str) -> dict:
    # Keep wrapper name stable for existing tests/imports.
    return stock_analytics.compute_stock_metrics(df, ticker, ticker_factory=yf.Ticker)


def _format_fundamental(val, is_pct=False):
    """Compatibility wrapper for tests and existing call-sites."""
    return _format_fundamental_component(val, is_pct=is_pct)


def _render_stock_cards(
    tickers: list[str],
    selected_universe: str,
    empty_message: str,
    show_liquidity_context: bool = False,
    stocks_per_row: int = 2,
    chart_height: float | None = None,
    row_layout: list[tuple[str, float]] | None = None,
) -> None:
    _shared_render_stock_cards(
        tickers=tickers,
        selected_universe=selected_universe,
        empty_message=empty_message,
        show_liquidity_context=show_liquidity_context,
        stocks_per_row=stocks_per_row,
        chart_height=chart_height,
        row_layout=row_layout,
    )


render_stock_cards = _render_stock_cards


def render_industry_stock_page(sector: str, industry: str) -> None:
    from .features.sector_industry_stocks.rendering import render_industry_stock_page as render_feature_page

    render_feature_page(sector=sector, industry=industry, render_stock_cards_fn=_render_stock_cards)


def render_favorites_page() -> None:
    from .features.favorites.rendering import render_favorites_page as render_feature_page

    render_feature_page(render_stock_cards_fn=_render_stock_cards)


def render_search_results_page() -> None:
    from .features.search.rendering import render_search_results_page as render_feature_page

    render_feature_page(render_stock_cards_fn=_render_stock_cards)


def _render_sector_industry_summary(universe: str, sector: str) -> None:
    from .features.sector_industry_stocks.rendering import render_sector_industry_summary as render_feature_page

    render_feature_page(universe=universe, sector=sector)


def render_sector_card(name: str, ticker: str) -> None:
    from .features.sector_industry_stocks.rendering import render_sector_card as render_feature_page

    render_feature_page(name=name, ticker=ticker)
