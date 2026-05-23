"""Sector, industry, and stock browsing rendering."""

import pandas as pd
import streamlit as st

from ...charts import get_trend_colors, render_chart
from ...core.analytics import compute_industry_aggregate, compute_return_vol_rr as compute_return_vol_rr_core
from ...core.constants import (
    INDUSTRY_GRID_COLS,
    SECTOR_FIGSIZE,
    SECTOR_GRID_COLS,
    resolve_industry_proxy_ticker,
    resolve_sector_proxy_ticker,
)
from ...core.data import (
    fetch_sector_data,
    get_sector_industry_counts,
    get_universe_industries,
    get_universe_sector_stock_count,
    get_universe_sectors,
    get_universe_tickers,
    load_universe,
)
from ...core.navigation import open_industry_stocks
from ...core.ui import render_data_card, render_stock_cards


FLOATING_CARD_WIDTH_PX = 400
FLOATING_CARD_HEIGHT_PX = 200
FLOATING_GRID_COLS = 3
FLOATING_CHART_FIGSIZE = (4.0, 1.55)


def _render_floating_grid_styles() -> None:
    st.markdown(
        f"""
        <style>
        .sector-floating-note {{
            font-size: 0.74rem;
            opacity: 0.72;
            margin-bottom: 0.35rem;
        }}
        .sector-floating-card [data-testid="stVerticalBlockBorderWrapper"] {{
            min-height: {FLOATING_CARD_HEIGHT_PX}px;
        }}
        .sector-floating-card h3 {{
            font-size: 0.92rem !important;
            margin-bottom: 0.1rem !important;
        }}
        .sector-floating-card .stCaption {{
            font-size: 0.68rem !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sector_grid(universe: str) -> None:
    _render_floating_grid_styles()
    universe_sectors = get_universe_sectors(universe)
    st.markdown(
        f'<div class="sector-floating-note">Floating sector overview tuned for about {FLOATING_CARD_WIDTH_PX}x{FLOATING_CARD_HEIGHT_PX}px cards.</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(FLOATING_GRID_COLS)
    for i, sector_name in enumerate(universe_sectors):
        with cols[i % FLOATING_GRID_COLS]:
            st.markdown('<div class="sector-floating-card">', unsafe_allow_html=True)
            etf_ticker = resolve_sector_proxy_ticker(universe, sector_name)
            if etf_ticker:
                render_sector_card(sector_name, etf_ticker)
            else:
                _render_universe_sector_card(universe, sector_name)
            st.markdown('</div>', unsafe_allow_html=True)


def render_industry_dashboard(
    sector: str | None,
    compute_return_vol_rr=None,
    render_data_card_fn=None,
    open_industry_stocks_fn=None,
) -> None:
    compute_return_vol_rr = compute_return_vol_rr or compute_return_vol_rr_core
    render_data_card_fn = render_data_card_fn or render_data_card
    open_industry_stocks_fn = open_industry_stocks_fn or open_industry_stocks

    selected_universe = st.session_state.get("selected_universe", "S&P 500")
    _render_floating_grid_styles()
    if sector:
        counts = get_sector_industry_counts(selected_universe, sector)
    else:
        df = load_universe(selected_universe)
        counts = (
            df.loc[df["Industry"].astype(str).str.strip() != ""]
            .groupby("Industry", sort=False)
            .size()
            .sort_index()
            .to_dict()
        )
    industries = [ind for ind in counts if ind != "undefined"]
    undef_count = counts.get("undefined", 0)
    total = sum(counts.values())

    if not counts:
        st.write("No industries found.")
        return

    st.caption(
        f"**{total} stocks** total - {len(industries)} industries"
        + (f" · **{undef_count} unclassified**" if undef_count else "")
    )

    st.markdown(
        f'<div class="sector-floating-note">Floating industry overview tuned for about {FLOATING_CARD_WIDTH_PX}x{FLOATING_CARD_HEIGHT_PX}px cards.</div>',
        unsafe_allow_html=True,
    )
    columns = st.columns(FLOATING_GRID_COLS)
    for i, industry in enumerate(industries):
        with columns[i % FLOATING_GRID_COLS]:
            st.markdown('<div class="sector-floating-card">', unsafe_allow_html=True)
            tickers = get_universe_tickers(selected_universe, sector=sector, industry=industry)
            count = len(tickers)
            proxy_ticker = resolve_industry_proxy_ticker(selected_universe, sector, industry)

            if proxy_ticker:
                with st.spinner(f"Loading {industry} proxy {proxy_ticker}..."):
                    proxy_df = fetch_sector_data(proxy_ticker)
                if not proxy_df.empty and "Close" in proxy_df.columns:
                    proxy_close = proxy_df["Close"]
                    proxy_volume = proxy_df["Volume"] if "Volume" in proxy_df.columns else pd.Series(dtype=float)
                    risk_metrics = compute_return_vol_rr(proxy_close, lookback=30)
                    render_data_card_fn(
                        title=f"{industry} ({proxy_ticker})",
                        close=proxy_close,
                        volume=proxy_volume,
                        chart_params={"y_label": "Index", "legend_label": proxy_ticker, "figsize": FLOATING_CHART_FIGSIZE},
                    )
                    st.caption(
                        f"Proxy ETF: {proxy_ticker} · Exp Vol (30D ann): {risk_metrics['exp_vol_ann_pct']:.1f}% · "
                        f"Risk/Reward: {risk_metrics['risk_reward']:+.2f}"
                    )
                else:
                    proxy_ticker = None

            if not proxy_ticker:
                if tickers:
                    with st.spinner(f"Building {industry} aggregate..."):
                        avg_close, total_volume, _ = compute_industry_aggregate(tickers)
                    risk_metrics = compute_return_vol_rr(avg_close, lookback=30)
                    render_data_card_fn(
                        title=f"{industry} ({count})",
                        close=avg_close,
                        volume=total_volume,
                        chart_params={"y_label": "Index", "legend_label": "Index", "figsize": FLOATING_CHART_FIGSIZE},
                    )
                    st.caption(
                        f"Exp Vol (30D ann): {risk_metrics['exp_vol_ann_pct']:.1f}% · "
                        f"Risk/Reward: {risk_metrics['risk_reward']:+.2f}"
                    )
                else:
                    st.subheader(f"{industry} ({count})")
                    st.caption("No data")

            _render_stock_list_controls(
                sector=sector,
                industry=industry,
                title=industry,
                count=count,
                tickers=tickers,
                open_industry_stocks_fn=open_industry_stocks_fn,
            )
            st.markdown('</div>', unsafe_allow_html=True)

    if undef_count:
        undef_tickers = get_universe_tickers(selected_universe, sector=sector, industry="undefined")
        col_idx = len(industries) % FLOATING_GRID_COLS
        with columns[col_idx]:
            st.markdown('<div class="sector-floating-card">', unsafe_allow_html=True)
            st.subheader(f"Unclassified ({undef_count})")
            st.caption("No industry assigned")
            _render_stock_list_controls(
                sector=sector,
                industry="undefined",
                title="Unclassified",
                count=undef_count,
                tickers=undef_tickers,
                open_industry_stocks_fn=open_industry_stocks_fn,
            )
            st.markdown('</div>', unsafe_allow_html=True)


def render_industry_stock_page(
    sector: str | None,
    industry: str,
    stock: str | None = None,
    render_stock_cards_fn=None,
) -> None:
    render_stock_cards_fn = render_stock_cards_fn or render_stock_cards

    selected_universe = st.session_state.get("selected_universe", "S&P 500")
    all_tickers = get_universe_tickers(selected_universe, sector=sector, industry=industry)
    if stock:
        all_tickers = [ticker for ticker in all_tickers if ticker == stock]
    st.caption(f"{len(all_tickers)} stocks in {selected_universe}")
    render_stock_cards_fn(
        tickers=all_tickers,
        selected_universe=selected_universe,
        empty_message="No stocks in this industry.",
    )
    st.success(f"✓ Complete! Displayed all {len(all_tickers)} stocks")


def render_sector_industry_summary(universe: str, sector: str) -> None:
    counts = get_sector_industry_counts(universe, sector)
    total = sum(counts.values())
    undef_count = counts.get("undefined", 0)
    assigned = total - undef_count

    st.caption(f"**{total} stocks** · {assigned} classified · {undef_count} unclassified")

    if counts:
        rows = []
        for industry, cnt in counts.items():
            label = "_(unclassified)_" if industry == "undefined" else industry
            rows.append(f"- {label}: **{cnt}**")
        st.markdown("\n".join(rows))


def render_sector_card(name: str, ticker: str) -> None:
    def open_industry_view() -> None:
        st.session_state.view = "industry"
        st.session_state.selected_sector = name
        st.session_state.pop("selected_industry", None)

    with st.spinner(f"Loading {name}..."):
        df = fetch_sector_data(ticker)
    close = df["Close"].squeeze() if not df.empty else pd.Series()
    volume = df["Volume"].squeeze() if not df.empty else pd.Series()

    st.subheader(f"{name} ({ticker})")
    if close.empty:
        st.write("No data available.")
    else:
        ma50 = close.rolling(50).mean()
        bg_color, bar_color = get_trend_colors(ma50)
        render_chart(
            close,
            volume,
            ma50,
            bg_color,
            bar_color,
            y_label="Price",
            legend_label="Price",
            figsize=SECTOR_FIGSIZE,
        )

    btn_col, info_col = st.columns([4, 1])
    with btn_col:
        st.button("View Industries", key=name, on_click=open_industry_view, use_container_width=True)
    with info_col:
        universe = st.session_state.get("selected_universe", "S&P 500")
        counts = get_sector_industry_counts(universe, name)
        total = get_universe_sector_stock_count(universe, name)
        undef = counts.get("undefined", 0)
        with st.popover("ⓘ", use_container_width=True):
            st.markdown(f"**{name}**")
            st.caption(f"Total stocks: {total}")
            st.caption(f"Classified: {total - undef}")
            if undef:
                st.caption(f"Unclassified: {undef}")
            for industry, cnt in counts.items():
                label = "Unclassified" if industry == "undefined" else industry
                st.caption(f"{label}: {cnt}")


def _render_stock_list_controls(
    *,
    sector: str | None,
    industry: str,
    title: str,
    count: int,
    tickers: list[str],
    open_industry_stocks_fn,
) -> None:
    btn_col, info_col = st.columns([4, 1])
    with btn_col:
        st.button(
            "View Stocks",
            key=f"stocks-{sector or 'all'}-{industry}",
            on_click=open_industry_stocks_fn,
            args=(sector, industry),
            use_container_width=True,
        )
    with info_col:
        with st.popover("ⓘ", use_container_width=True):
            st.markdown(f"**{title}**")
            st.caption(f"{count} stocks")
            for ticker in tickers:
                st.caption(ticker)


def _render_universe_sector_card(universe: str, sector: str) -> None:
    def open_industry_view() -> None:
        st.session_state.view = "industry"
        st.session_state.selected_sector = sector
        st.session_state.pop("selected_industry", None)

    st.subheader(sector)
    btn_col, info_col = st.columns([4, 1])
    with btn_col:
        st.button(
            "View Industries",
            key=f"universe-sector-{universe}-{sector}",
            on_click=open_industry_view,
            use_container_width=True,
        )
    with info_col:
        counts = get_sector_industry_counts(universe, sector)
        total = get_universe_sector_stock_count(universe, sector)
        undef = counts.get("undefined", 0)
        with st.popover("ⓘ", use_container_width=True):
            st.markdown(f"**{sector}**")
            st.caption(f"Total stocks: {total}")
            st.caption(f"Classified: {total - undef}")
            if undef:
                st.caption(f"Unclassified: {undef}")
            for industry, cnt in counts.items():
                label = "Unclassified" if industry == "undefined" else industry
                st.caption(f"{label}: {cnt}")
