"""Suggestions feature rendering.

The feature scans industries and stocks within the selected universe using
trend and volume criteria.
"""

import math

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from ...core.analytics import compute_industry_aggregate
from ...core.constants import (
    INDEX_START_VALUE,
    TICKER_PERIOD,
    resolve_industry_proxy_ticker,
    resolve_sector_proxy_ticker,
)
from ...core.data import (
    fetch_ticker_data_batch,
    fetch_sector_data,
    get_universe_industries,
    get_universe_stock_name,
    get_universe_tickers,
    load_universe,
)


LOOKBACK_BARS = 150
MA_TREND_WINDOW = 1
VOLUME_RECENT_WINDOW = 10
VOLUME_BASE_WINDOW = 30
MIN_VOLUME_RATIO = 1.10
HIGH_TRADE_WINDOW = 20
MICRO_CHART_SIZE = (1.0, 0.5)
MICRO_CHART_DPI = 100


def _to_series(values: pd.Series | pd.DataFrame | None) -> pd.Series:
    if isinstance(values, pd.Series):
        return pd.to_numeric(values, errors="coerce").dropna()
    if isinstance(values, pd.DataFrame):
        if "Close" in values.columns:
            return pd.to_numeric(values["Close"], errors="coerce").dropna()
        if values.shape[1] > 0:
            return pd.to_numeric(values.iloc[:, 0], errors="coerce").dropna()
    return pd.Series(dtype=float)


def _volume_ratio(volume: pd.Series, recent_window: int, base_window: int) -> float:
    volume = _to_series(volume)
    if len(volume) < recent_window + base_window:
        return 0.0
    recent = float(volume.tail(recent_window).mean())
    baseline = float(volume.tail(recent_window + base_window).head(base_window).mean())
    if baseline <= 0:
        return 0.0
    return recent / baseline


def _ma_trend_pct(close: pd.Series, ma_window: int = 50, trend_window: int = 10) -> float:
    close = _to_series(close)
    ma = close.rolling(ma_window).mean().dropna()
    if len(ma) <= trend_window:
        return 0.0
    current = float(ma.iloc[-1])
    previous = float(ma.iloc[-(trend_window + 1)])
    if not math.isfinite(current) or not math.isfinite(previous) or previous == 0:
        return 0.0
    return (current / previous - 1.0) * 100.0


def _limit_series(values: pd.Series, bars: int = LOOKBACK_BARS) -> pd.Series:
    values = _to_series(values)
    if values.empty:
        return values
    return values.tail(bars)


def _avg_dollar_volume(close: pd.Series, volume: pd.Series, window: int = HIGH_TRADE_WINDOW) -> float:
    close = _to_series(close)
    volume = _to_series(volume)
    aligned_idx = close.index.intersection(volume.index)
    if aligned_idx.empty:
        return 0.0
    dollar = (close.loc[aligned_idx] * volume.loc[aligned_idx]).dropna()
    if len(dollar) < window:
        return 0.0
    return float(dollar.tail(window).mean())


def _load_ticker_data(ticker: str, period: str) -> pd.DataFrame:
    """Load ticker data, reusing shared cached path when possible."""
    if period == TICKER_PERIOD:
        _, df = fetch_ticker_data_batch(ticker, force_refresh=False)
        if df is not None and not df.empty:
            return df
    return fetch_sector_data(ticker, period=period)


def _compute_industry_aggregate_for_period(
    tickers: list[str],
    period: str,
) -> tuple[pd.Series, pd.Series, int]:
    if period == TICKER_PERIOD:
        return compute_industry_aggregate(tickers)

    if not tickers:
        return pd.Series(dtype=float), pd.Series(dtype=float), 0

    closes: list[pd.Series] = []
    volumes: list[pd.Series] = []
    for ticker in tickers:
        df = _load_ticker_data(ticker, period)
        if df is None or df.empty or "Close" not in df.columns or "Volume" not in df.columns:
            continue
        close_series = _to_series(df["Close"])
        volume_series = _to_series(df["Volume"])
        if close_series.empty or volume_series.empty:
            continue
        aligned_idx = close_series.index.intersection(volume_series.index)
        if aligned_idx.empty:
            continue
        closes.append(close_series.loc[aligned_idx])
        volumes.append(volume_series.loc[aligned_idx])

    num_fetched = len(closes)
    if num_fetched == 0:
        return pd.Series(dtype=float), pd.Series(dtype=float), 0

    close_df = pd.concat(closes, axis=1, keys=[f"ticker_{i}" for i in range(num_fetched)]).ffill().dropna(axis=0, how="all")
    volume_df = pd.concat(volumes, axis=1, keys=[f"ticker_{i}" for i in range(num_fetched)]).fillna(0)
    pct_changes = close_df.pct_change().mean(axis=1, skipna=True)
    index = (1 + pct_changes).cumprod() * INDEX_START_VALUE
    total_volume = volume_df.sum(axis=1)
    return index, total_volume, num_fetched


def _proxy_volume_ratio(
    ticker: str | None,
    period: str,
    recent_window: int,
    base_window: int,
) -> float | None:
    if not ticker:
        return None
    df = _load_ticker_data(ticker, period)
    if df is None or df.empty or "Volume" not in df.columns:
        return None
    volume = _limit_series(df["Volume"])
    if volume.empty:
        return None
    ratio = _volume_ratio(volume, recent_window=recent_window, base_window=base_window)
    return float(ratio) if math.isfinite(ratio) else None


def _render_micro_chart(close: pd.Series) -> None:
    close = _limit_series(close)
    if close.empty:
        st.caption("n/a")
        return

    ma50 = close.rolling(50).mean()
    ma150 = close.rolling(150).mean()

    fig, ax = plt.subplots(figsize=MICRO_CHART_SIZE, dpi=MICRO_CHART_DPI)
    ax.set_facecolor("none")
    fig.patch.set_alpha(0)
    ax.plot(close.index, close.values, color="#e6e6e6", linewidth=0.8)
    ax.plot(ma50.index, ma50.values, color="#ffdd44", linewidth=0.75)
    if ma150.notna().any():
        ax.plot(ma150.index, ma150.values, color="#00aaff", linewidth=0.7)

    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout(pad=0.1)
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)


def _render_industry_micro_charts(universe: str, suggestions: pd.DataFrame) -> None:
    st.caption("Industry mini charts")
    cols_per_row = 4
    cols = st.columns(cols_per_row)
    for idx, (_, row) in enumerate(suggestions.iterrows()):
        industry = str(row.get("industry", ""))
        sector = str(row.get("sector", ""))
        if not industry:
            continue

        tickers = get_universe_tickers(universe, industry=industry)
        close, _volume, _fetched = _compute_industry_aggregate_for_period(tickers, TICKER_PERIOD)
        with cols[idx % cols_per_row]:
            st.caption(f"{industry} ({sector})" if sector else industry)
            _render_micro_chart(close)


def _render_stock_micro_charts(universe: str, stocks: pd.DataFrame) -> None:
    st.caption("Stock mini charts")
    cols_per_row = 4
    cols = st.columns(cols_per_row)
    for idx, (_, row) in enumerate(stocks.iterrows()):
        ticker = str(row.get("ticker", ""))
        if not ticker:
            continue
        company = get_universe_stock_name(universe, ticker)
        df = _load_ticker_data(ticker, TICKER_PERIOD)
        close = pd.Series(dtype=float)
        if df is not None and not df.empty and "Close" in df.columns:
            close = _to_series(df["Close"])

        with cols[idx % cols_per_row]:
            st.caption(f"{ticker} - {company}")
            _render_micro_chart(close)


@st.cache_data(ttl=900, show_spinner=False)
def get_suggested_industries(
    universe: str,
    period: str = TICKER_PERIOD,
    industry_trend_window: int = MA_TREND_WINDOW,
    volume_recent_window: int = VOLUME_RECENT_WINDOW,
    volume_base_window: int = VOLUME_BASE_WINDOW,
    min_volume_ratio: float = MIN_VOLUME_RATIO,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    universe_df = load_universe(universe)

    for industry in get_universe_industries(universe, None):
        tickers = get_universe_tickers(universe, industry=industry)
        if not tickers:
            continue

        close, volume, fetched = _compute_industry_aggregate_for_period(tickers, period)
        close_series = _limit_series(close)
        volume_series = _limit_series(volume)
        if close_series.empty or volume_series.empty or fetched == 0:
            continue

        ma50_trend_pct = _ma_trend_pct(close_series, ma_window=50, trend_window=industry_trend_window)
        volume_jump_ratio = _volume_ratio(
            volume_series,
            recent_window=volume_recent_window,
            base_window=volume_base_window,
        )

        if ma50_trend_pct <= 0.0 or volume_jump_ratio < min_volume_ratio:
            continue

        sector = ""
        if not universe_df.empty:
            industry_rows = universe_df[universe_df["Industry"] == industry]
            if not industry_rows.empty:
                modes = industry_rows["Sector"].mode()
                if not modes.empty:
                    sector = str(modes.iloc[0])

        sector_proxy = resolve_sector_proxy_ticker(universe, sector) if sector else None
        industry_proxy = resolve_industry_proxy_ticker(universe, sector or None, industry)
        sector_proxy_volume_ratio = _proxy_volume_ratio(
            sector_proxy,
            period,
            recent_window=volume_recent_window,
            base_window=volume_base_window,
        )
        industry_proxy_volume_ratio = _proxy_volume_ratio(
            industry_proxy,
            period,
            recent_window=volume_recent_window,
            base_window=volume_base_window,
        )

        rows.append(
            {
                "industry": industry,
                "sector": sector,
                "sector_etf": sector_proxy or "",
                "industry_etf": industry_proxy or "",
                "stock_count": len(tickers),
                "ma50_trend_pct": float(ma50_trend_pct),
                "volume_ratio": float(volume_jump_ratio),
                "sector_etf_volume_ratio": sector_proxy_volume_ratio,
                "industry_etf_volume_ratio": industry_proxy_volume_ratio,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "industry",
                "sector",
                "sector_etf",
                "industry_etf",
                "stock_count",
                "ma50_trend_pct",
                "volume_ratio",
                "sector_etf_volume_ratio",
                "industry_etf_volume_ratio",
            ]
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["ma50_trend_pct", "volume_ratio", "industry"], ascending=[False, False, True])
        .reset_index(drop=True)
    )


@st.cache_data(ttl=900, show_spinner=False)
def get_suggested_industry_stocks(
    universe: str,
    industry: str,
    period: str = TICKER_PERIOD,
    stock_trend_window: int = MA_TREND_WINDOW,
    volume_recent_window: int = VOLUME_RECENT_WINDOW,
    volume_base_window: int = VOLUME_BASE_WINDOW,
    min_volume_ratio: float = MIN_VOLUME_RATIO,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    tickers = get_universe_tickers(universe, industry=industry)

    for ticker in tickers:
        df = _load_ticker_data(ticker, period)
        if df.empty or "Close" not in df.columns or "Volume" not in df.columns:
            continue

        close = _limit_series(df["Close"])
        volume = _limit_series(df["Volume"])
        if close.empty or volume.empty:
            continue

        ma50_trend_pct = _ma_trend_pct(close, ma_window=50, trend_window=stock_trend_window)
        if ma50_trend_pct <= 0.0:
            continue

        ma150 = close.rolling(150).mean().dropna()
        if ma150.empty:
            continue

        latest_price = float(close.iloc[-1])
        latest_ma150 = float(ma150.iloc[-1])
        if not math.isfinite(latest_price) or not math.isfinite(latest_ma150):
            continue
        if latest_price <= latest_ma150:
            continue

        volume_jump_ratio = _volume_ratio(
            volume,
            recent_window=volume_recent_window,
            base_window=volume_base_window,
        )
        if volume_jump_ratio < min_volume_ratio:
            continue

        rows.append(
            {
                "ticker": ticker,
                "name": get_universe_stock_name(universe, ticker),
                "price": latest_price,
                "ma150": latest_ma150,
                "ma50_trend_pct": float(ma50_trend_pct),
                "volume_ratio": float(volume_jump_ratio),
                "avg_dollar_volume_20d": _avg_dollar_volume(close, volume, window=HIGH_TRADE_WINDOW),
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "ticker",
                "name",
                "price",
                "ma150",
                "ma50_trend_pct",
                "volume_ratio",
                "avg_dollar_volume_20d",
            ]
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["avg_dollar_volume_20d", "ma50_trend_pct", "volume_ratio", "ticker"], ascending=[False, False, False, True])
        .reset_index(drop=True)
    )


def suggestions_refresh_tickers(
    universe: str,
    period: str = TICKER_PERIOD,
    industry_trend_window: int = MA_TREND_WINDOW,
    volume_recent_window: int = VOLUME_RECENT_WINDOW,
    volume_base_window: int = VOLUME_BASE_WINDOW,
    min_volume_ratio: float = MIN_VOLUME_RATIO,
) -> list[str]:
    suggestions = get_suggested_industries(
        universe,
        period,
        industry_trend_window,
        volume_recent_window,
        volume_base_window,
        min_volume_ratio,
    )
    if suggestions.empty:
        return get_universe_tickers(universe)

    refresh: list[str] = []
    for industry in suggestions["industry"].tolist():
        refresh.extend(get_universe_tickers(universe, industry=industry))

    if "sector_etf" in suggestions.columns:
        refresh.extend([t for t in suggestions["sector_etf"].tolist() if t])
    if "industry_etf" in suggestions.columns:
        refresh.extend([t for t in suggestions["industry_etf"].tolist() if t])

    return list(dict.fromkeys(refresh))


def _open_browse_industry(universe: str, industry: str, sector: str | None) -> None:
    st.session_state["selected_universe"] = universe
    st.session_state["nav_universe"] = universe
    st.session_state["selected_industry"] = industry
    st.session_state["nav_industry"] = industry
    if sector:
        st.session_state["selected_sector"] = sector
        st.session_state["nav_sector"] = sector
    st.session_state.pop("selected_stock", None)
    st.session_state.pop("nav_stock", None)
    st.session_state["nav_feature"] = "browse"
    st.session_state["view"] = "industry_stocks"
    st.rerun()


def render_suggestions_view(
    universe: str,
) -> None:
    st.subheader("Suggestions")
    st.caption(
        "Buy setup: positive 50-day MA trend, price above 150-day MA, and recent volume increase. "
        "Ranked by higher trading activity using the latest 150 trading days."
    )

    suggestions = get_suggested_industries(universe)
    if suggestions.empty:
        st.info("No industries currently match the suggestion criteria for this universe.")
        st.session_state.pop("suggestions_selected_industry", None)
        return

    display = suggestions.copy()
    display["50D MA Trend %"] = display["ma50_trend_pct"].map(lambda v: f"{v:+.2f}%")
    display["Industry Volume"] = display["volume_ratio"].map(lambda v: f"{v:.2f}x")
    display["Sector ETF Vol"] = display["sector_etf_volume_ratio"].map(
        lambda v: f"{v:.2f}x" if pd.notna(v) else "n/a"
    )
    display["Industry ETF Vol"] = display["industry_etf_volume_ratio"].map(
        lambda v: f"{v:.2f}x" if pd.notna(v) else "n/a"
    )
    display = display.rename(
        columns={
            "industry": "Industry",
            "sector": "Sector",
            "stock_count": "Stocks",
        }
    )[["Industry", "Sector", "Stocks", "50D MA Trend %", "Industry Volume", "Sector ETF Vol", "Industry ETF Vol"]]

    st.dataframe(display, use_container_width=True, hide_index=True)
    _render_industry_micro_charts(universe, suggestions)

    options = ["— select suggested industry —"] + suggestions["industry"].tolist()
    current = st.session_state.get("suggestions_selected_industry", "— select suggested industry —")
    if current not in options:
        current = "— select suggested industry —"

    selected_industry = st.selectbox(
        "Suggested industries",
        options,
        index=options.index(current),
        key="suggestions_selected_industry",
    )

    if selected_industry == "— select suggested industry —":
        return

    st.markdown(f"### Suggested Stocks: {selected_industry}")
    stocks = get_suggested_industry_stocks(
        universe,
        selected_industry,
    )
    if stocks.empty:
        st.info("No stocks currently match all criteria in this industry.")
        return

    sector_match = suggestions.loc[suggestions["industry"] == selected_industry, "sector"]
    selected_sector_name = str(sector_match.iloc[0]) if not sector_match.empty else ""

    browse_col, _ = st.columns([3, 7])
    with browse_col:
        if st.button(
            "Open In Sector Browser",
            key=f"open-suggested-{universe}-{selected_industry}",
            use_container_width=True,
        ):
            _open_browse_industry(universe, selected_industry, selected_sector_name or None)

    stocks_display = stocks.copy()
    stocks_display["Price"] = stocks_display["price"].map(lambda v: f"${v:.2f}")
    stocks_display["MA150"] = stocks_display["ma150"].map(lambda v: f"${v:.2f}")
    stocks_display["50D MA Trend %"] = stocks_display["ma50_trend_pct"].map(lambda v: f"{v:+.2f}%")
    stocks_display["Volume Increase"] = stocks_display["volume_ratio"].map(lambda v: f"{v:.2f}x")
    stocks_display["Avg $ Volume (20D)"] = stocks_display["avg_dollar_volume_20d"].map(
        lambda v: f"${v / 1_000_000:.1f}M"
    )
    stocks_display = stocks_display.rename(columns={"ticker": "Ticker", "name": "Name"})[
        ["Ticker", "Name", "Price", "MA150", "50D MA Trend %", "Volume Increase", "Avg $ Volume (20D)"]
    ]

    st.dataframe(stocks_display, use_container_width=True, hide_index=True)
    _render_stock_micro_charts(universe, stocks)
