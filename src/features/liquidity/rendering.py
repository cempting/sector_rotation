import math
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from ...core.analytics import compute_industry_aggregate
from ...core.constants import resolve_sector_proxy_ticker
from ...core.data import (
    fetch_sector_data,
    get_sector_industry_counts,
    get_universe_sectors,
    get_universe_tickers,
    list_universes,
)


_MARKET_PROXIES = [
    {"label": "US", "ticker": "SPY", "bucket": "Markets"},
    {"label": "Europe", "ticker": "EZU", "bucket": "Markets"},
    {"label": "Hong Kong", "ticker": "EWH", "bucket": "Markets"},
    {"label": "Australia", "ticker": "EWA", "bucket": "Markets"},
    {"label": "Brazil", "ticker": "EWZ", "bucket": "Markets"},
    {"label": "South Africa", "ticker": "EZA", "bucket": "Markets"},
]

_CROSS_ASSET_PROXIES = [
    {"label": "US Equities", "ticker": "SPY", "bucket": "Risk"},
    {"label": "Small Caps", "ticker": "IWM", "bucket": "Risk"},
    {"label": "EM Equities", "ticker": "EEM", "bucket": "Risk"},
    {"label": "HY Credit", "ticker": "HYG", "bucket": "Risk"},
    {"label": "IG Credit", "ticker": "LQD", "bucket": "Credit"},
    {"label": "Treasuries 20Y", "ticker": "TLT", "bucket": "Rates"},
    {"label": "Treasuries 7-10Y", "ticker": "IEF", "bucket": "Rates"},
    {"label": "Gold", "ticker": "GLD", "bucket": "Metals"},
    {"label": "Silver", "ticker": "SLV", "bucket": "Metals"},
    {"label": "Broad Commodities", "ticker": "DBC", "bucket": "Commodities"},
    {"label": "US Dollar", "ticker": "UUP", "bucket": "FX"},
    {"label": "Cash", "ticker": "BIL", "bucket": "Cash"},
]

_SENTIMENT_PROXIES = {
    "risk_equity": "SPY",
    "small_caps": "IWM",
    "high_yield": "HYG",
    "ig_credit": "LQD",
    "treasuries": "TLT",
    "gold": "GLD",
    "usd": "UUP",
    "vix": "^VIX",
}


def _to_series(values: pd.Series | pd.DataFrame | np.ndarray | float | int | None) -> pd.Series:
    if isinstance(values, pd.Series):
        return values.dropna()
    if isinstance(values, pd.DataFrame):
        if "Close" in values.columns:
            return values["Close"].dropna()
        if values.shape[1] > 0:
            return values.iloc[:, 0].dropna()
        return pd.Series(dtype=float)
    if values is None:
        return pd.Series(dtype=float)
    return pd.Series([values], dtype=float)


def _safe_metrics(
    close: pd.Series,
    volume: pd.Series,
    long_lookback: int = 20,
    short_lookback: int = 5,
    volume_recent: int = 5,
    volume_base: int = 20,
) -> dict[str, float] | None:
    close = _to_series(close)
    volume = _to_series(volume)
    required = max(long_lookback + 1, short_lookback + 1, volume_recent + volume_base)
    if len(close) < required:
        return None

    last = float(close.iloc[-1])
    back_long = float(close.iloc[-(long_lookback + 1)])
    back_short = float(close.iloc[-(short_lookback + 1)])
    if back_long <= 0 or back_short <= 0:
        return None

    ret_20 = (last / back_long) - 1
    ret_5 = (last / back_short) - 1

    vol_jump = 1.0
    if len(volume) >= volume_recent + volume_base:
        recent = float(volume.tail(volume_recent).mean())
        base = float(volume.tail(volume_recent + volume_base).head(volume_base).mean())
        if base > 0:
            vol_jump = recent / base

    return {
        "ret_20": ret_20,
        "ret_5": ret_5,
        "vol_jump": vol_jump,
    }


def _zscore(series: pd.Series) -> pd.Series:
    std = float(series.std(ddof=0))
    if std == 0 or math.isnan(std):
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - float(series.mean())) / std


def _latest_close(ticker: str, period: str = "1y") -> pd.Series:
    df = fetch_sector_data(ticker, period=period)
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)
    return _to_series(df["Close"])


@st.cache_data(ttl=900, show_spinner=False)
def get_market_sentiment_snapshot(period: str = "1y") -> dict[str, float | str]:
    spy = _latest_close(_SENTIMENT_PROXIES["risk_equity"], period)
    iwm = _latest_close(_SENTIMENT_PROXIES["small_caps"], period)
    hyg = _latest_close(_SENTIMENT_PROXIES["high_yield"], period)
    lqd = _latest_close(_SENTIMENT_PROXIES["ig_credit"], period)
    tlt = _latest_close(_SENTIMENT_PROXIES["treasuries"], period)
    gld = _latest_close(_SENTIMENT_PROXIES["gold"], period)
    uup = _latest_close(_SENTIMENT_PROXIES["usd"], period)
    vix = _latest_close(_SENTIMENT_PROXIES["vix"], period)

    def ret(series: pd.Series, lb: int = 20) -> float:
        if len(series) < lb + 1:
            return 0.0
        prev = float(series.iloc[-(lb + 1)])
        if prev <= 0:
            return 0.0
        return float(series.iloc[-1] / prev - 1)

    risk_score = (
        1.4 * ret(spy)
        + 0.8 * (ret(iwm) - ret(spy))
        + 0.8 * (ret(hyg) - ret(lqd))
        - 0.6 * ret(tlt)
        - 0.3 * ret(gld)
        - 0.4 * ret(uup)
    )

    vix_level = float(vix.iloc[-1]) if not vix.empty else 0.0
    vix_chg_20d = ret(vix)
    vix_penalty = max(0.0, (vix_level - 18.0) / 12.0) + max(0.0, vix_chg_20d)

    fear_greed = (risk_score - vix_penalty + 1.5) / 3.0
    fear_greed = max(0.0, min(1.0, fear_greed)) * 100.0

    if fear_greed >= 70:
        sentiment = "Greed"
    elif fear_greed >= 55:
        sentiment = "Risk-On"
    elif fear_greed <= 30:
        sentiment = "Fear"
    elif fear_greed <= 45:
        sentiment = "Risk-Off"
    else:
        sentiment = "Neutral"

    return {
        "sentiment": sentiment,
        "fear_greed": float(fear_greed),
        "vix": float(vix_level),
        "vix_chg_20d_pct": float(vix_chg_20d * 100.0),
        "risk_score": float(risk_score),
    }


def compute_liquidity_scores(rows: list[dict[str, object]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["label", "ticker", "bucket", "ret_20", "ret_5", "vol_jump", "liquidity"])  # pragma: no cover

    df = pd.DataFrame(rows)
    z20 = _zscore(df["ret_20"].astype(float))
    z5 = _zscore(df["ret_5"].astype(float))
    zv = _zscore((df["vol_jump"].astype(float) - 1.0).fillna(0.0))

    score = 0.6 * z20 + 0.3 * z5 + 0.1 * zv
    df["liquidity"] = (score * 25.0).clip(-100.0, 100.0)
    return df.sort_values("liquidity", ascending=False).reset_index(drop=True)


def build_flow_edges(nodes: pd.DataFrame, max_edges: int = 5) -> list[dict[str, object]]:
    if nodes.empty:
        return []

    inflows = nodes.sort_values("liquidity", ascending=False).head(max_edges)
    outflows = nodes.sort_values("liquidity", ascending=True).head(max_edges)

    edges: list[dict[str, object]] = []
    for i in range(min(len(inflows), len(outflows))):
        src = outflows.iloc[i]
        dst = inflows.iloc[i]
        magnitude = min(abs(float(src["liquidity"])), float(dst["liquidity"]))
        if magnitude <= 2:
            continue
        edges.append(
            {
                "from": str(src["label"]),
                "to": str(dst["label"]),
                "magnitude": round(float(magnitude), 1),
            }
        )
    return edges


def classify_liquidity_regime(nodes: pd.DataFrame) -> str:
    if nodes.empty:
        return "No Signal"

    bucket_means = nodes.groupby("bucket")["liquidity"].mean().to_dict()
    risk = np.mean([bucket_means.get("Risk", 0.0), bucket_means.get("Markets", 0.0)])
    defense = np.mean([
        bucket_means.get("Rates", 0.0),
        bucket_means.get("Cash", 0.0),
        bucket_means.get("FX", 0.0),
        bucket_means.get("Metals", 0.0),
    ])

    spread = float(risk - defense)
    if spread >= 8:
        return "Risk-On"
    if spread <= -8:
        return "Risk-Off"
    if bucket_means.get("Metals", 0.0) > 8 and bucket_means.get("Risk", 0.0) < 0:
        return "Inflation Hedge"
    return "Rotation / Neutral"


def _collect_proxy_rows(
    proxies: Iterable[dict[str, str]],
    period: str,
    long_lookback: int,
    short_lookback: int,
    volume_recent: int,
    volume_base: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in proxies:
        ticker = item["ticker"]
        df = fetch_sector_data(ticker, period=period)
        if df.empty or "Close" not in df.columns:
            continue
        metrics = _safe_metrics(
            df["Close"],
            df["Volume"] if "Volume" in df.columns else pd.Series(dtype=float),
            long_lookback=long_lookback,
            short_lookback=short_lookback,
            volume_recent=volume_recent,
            volume_base=volume_base,
        )
        if not metrics:
            continue
        rows.append({
            "label": item["label"],
            "ticker": ticker,
            "bucket": item["bucket"],
            **metrics,
        })
    return rows


def _collect_sector_rows(
    universe: str,
    period: str,
    long_lookback: int,
    short_lookback: int,
    volume_recent: int,
    volume_base: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for sector in get_universe_sectors(universe):
        proxy = resolve_sector_proxy_ticker(universe, sector)
        if not proxy:
            continue
        df = fetch_sector_data(proxy, period=period)
        if df.empty or "Close" not in df.columns:
            continue
        metrics = _safe_metrics(
            df["Close"],
            df["Volume"] if "Volume" in df.columns else pd.Series(dtype=float),
            long_lookback=long_lookback,
            short_lookback=short_lookback,
            volume_recent=volume_recent,
            volume_base=volume_base,
        )
        if not metrics:
            continue
        rows.append({
            "label": sector,
            "ticker": proxy,
            "bucket": "Sectors",
            **metrics,
        })
    return rows


def _collect_sector_rows_all_markets(
    period: str,
    long_lookback: int,
    short_lookback: int,
    volume_recent: int,
    volume_base: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    seen_keys: set[tuple[str, str]] = set()

    for universe in list_universes():
        for sector in get_universe_sectors(universe):
            proxy = resolve_sector_proxy_ticker(universe, sector)
            if not proxy:
                continue

            dedupe_key = (universe, proxy)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            df = fetch_sector_data(proxy, period=period)
            if df.empty or "Close" not in df.columns:
                continue
            metrics = _safe_metrics(
                df["Close"],
                df["Volume"] if "Volume" in df.columns else pd.Series(dtype=float),
                long_lookback=long_lookback,
                short_lookback=short_lookback,
                volume_recent=volume_recent,
                volume_base=volume_base,
            )
            if not metrics:
                continue
            rows.append(
                {
                    "label": sector,
                    "ticker": proxy,
                    "bucket": "Sectors",
                    "universe": universe,
                    **metrics,
                }
            )

    if not rows:
        return []

    grouped_df = pd.DataFrame(rows)
    aggregated: list[dict[str, object]] = []
    for sector, grp in grouped_df.groupby("label", sort=True):
        members = sorted(grp["universe"].astype(str).unique().tolist())
        count = len(members)
        avg_ret_20 = float(grp["ret_20"].mean())
        avg_ret_5 = float(grp["ret_5"].mean())
        avg_vol_jump = float(grp["vol_jump"].mean())
        aggregated.append(
            {
                "label": str(sector),
                "ticker": f"{count} mkts",
                "bucket": "Sectors",
                "ret_20": avg_ret_20,
                "ret_5": avg_ret_5,
                "vol_jump": avg_vol_jump,
                "market_count": count,
                "members": ", ".join(members),
            }
        )
    return aggregated


def _collect_industry_rows(
    universe: str,
    sector: str,
    long_lookback: int,
    short_lookback: int,
    volume_recent: int,
    volume_base: int,
    max_industries: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    counts = get_sector_industry_counts(universe, sector)
    industry_order = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    for industry, _count in industry_order[:max_industries]:
        tickers = get_universe_tickers(universe, sector=sector, industry=industry)
        if len(tickers) < 2:
            continue
        close, volume, fetched = compute_industry_aggregate(tickers[:40])
        if fetched < 2:
            continue
        metrics = _safe_metrics(
            close,
            volume,
            long_lookback=long_lookback,
            short_lookback=short_lookback,
            volume_recent=volume_recent,
            volume_base=volume_base,
        )
        if not metrics:
            continue
        rows.append({
            "label": industry if industry != "undefined" else "Unclassified",
            "ticker": f"{fetched} stocks",
            "bucket": "Industries",
            **metrics,
        })
    return rows


@st.cache_data(ttl=900, show_spinner=False)
def get_liquidity_nodes(
    universe: str,
    selected_sector: str | None,
    layer: str,
    all_markets: bool,
    period: str,
    long_lookback: int,
    short_lookback: int,
    volume_recent: int,
    volume_base: int,
    max_industries: int,
) -> pd.DataFrame:
    if layer == "Cross-Asset":
        rows = _collect_proxy_rows(_CROSS_ASSET_PROXIES, period, long_lookback, short_lookback, volume_recent, volume_base)
    elif layer == "Markets":
        rows = _collect_proxy_rows(_MARKET_PROXIES, period, long_lookback, short_lookback, volume_recent, volume_base)
    elif layer == "Sectors":
        if all_markets:
            rows = _collect_sector_rows_all_markets(period, long_lookback, short_lookback, volume_recent, volume_base)
        else:
            rows = _collect_sector_rows(universe, period, long_lookback, short_lookback, volume_recent, volume_base)
    else:
        sector = selected_sector
        if not sector:
            sectors = get_universe_sectors(universe)
            sector = sectors[0] if sectors else ""
        rows = (
            _collect_industry_rows(
                universe,
                sector,
                long_lookback,
                short_lookback,
                volume_recent,
                volume_base,
                max_industries,
            )
            if sector
            else []
        )
    return compute_liquidity_scores(rows)


def liquidity_refresh_tickers(universe: str, selected_sector: str | None, all_markets: bool = False) -> list[str]:
    tickers = {item["ticker"] for item in _CROSS_ASSET_PROXIES}
    tickers.update(item["ticker"] for item in _MARKET_PROXIES)
    tickers.update(_SENTIMENT_PROXIES.values())
    universes = list_universes() if all_markets else [universe]

    for univ in universes:
        for sector in get_universe_sectors(univ):
            proxy = resolve_sector_proxy_ticker(univ, sector)
            if proxy:
                tickers.add(proxy)

    if (not all_markets) and selected_sector:
        counts = get_sector_industry_counts(universe, selected_sector)
        for industry, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:12]:
            for ticker in get_universe_tickers(universe, sector=selected_sector, industry=industry)[:20]:
                tickers.add(ticker)
    return sorted(tickers)


def _render_chessboard(nodes: pd.DataFrame, edges: list[dict[str, object]], title: str) -> None:
    if nodes.empty:
        st.warning("Not enough data to build a liquidity board yet.")
        return

    # Use a denser grid: 3 columns for few items, 4 for many.
    if len(nodes) <= 6:
        cols = 3
    else:
        cols = 4
    n = len(nodes)
    rows = int(math.ceil(n / cols))

    fig, ax = plt.subplots(figsize=(12, max(3.0, rows * 1.45)))
    cmap = plt.get_cmap("RdYlGn")
    positions: dict[str, tuple[float, float]] = {}

    for idx, row in nodes.reset_index(drop=True).iterrows():
        x = idx % cols
        y = rows - 1 - (idx // cols)
        value = float(row["liquidity"])
        color = cmap((value + 100.0) / 200.0)
        rect = plt.Rectangle((x + 0.02, y + 0.02), 0.91, 0.91, color=color, ec="#1f2937", lw=0.8)
        ax.add_patch(rect)
        label = str(row["label"])
        ticker = str(row["ticker"])
        ax.text(x + 0.475, y + 0.62, label, ha="center", va="center", fontsize=7.2, fontweight="bold")
        ax.text(x + 0.475, y + 0.44, ticker, ha="center", va="center", fontsize=6.2, color="#1f2937")
        ax.text(x + 0.475, y + 0.22, f"LQ {value:+.1f} pts", ha="center", va="center", fontsize=6.4)
        positions[label] = (x + 0.475, y + 0.475)

    for edge in edges[:4]:
        src = positions.get(str(edge["from"]))
        dst = positions.get(str(edge["to"]))
        if not src or not dst:
            continue
        lw = 0.8 + float(edge["magnitude"]) / 35.0
        ax.annotate("", xy=dst, xytext=src, arrowprops={"arrowstyle": "->", "lw": lw, "color": "#0ea5e9", "alpha": 0.9})

    ax.set_xlim(0, cols)
    ax.set_ylim(0, rows)
    ax.axis("off")
    ax.set_title(title, fontsize=10, pad=6)
    fig.tight_layout(pad=0.2)
    st.pyplot(fig)
    plt.close(fig)


def _industry_kind(industry_label: str) -> str:
    s = (industry_label or "").lower()
    if any(k in s for k in ["software", "semiconductor", "hardware", "internet", "technology", "it "]):
        return "Technology"
    if any(k in s for k in ["bank", "insurance", "financial", "capital", "asset", "broker"]):
        return "Financials"
    if any(k in s for k in ["health", "pharma", "biotech", "medical", "care"]):
        return "Healthcare"
    if any(k in s for k in ["oil", "gas", "energy", "drilling", "exploration"]):
        return "Energy"
    if any(k in s for k in ["material", "metal", "mining", "chemical", "steel"]):
        return "Materials"
    if any(k in s for k in ["retail", "consumer", "apparel", "food", "beverage", "household"]):
        return "Consumer"
    if any(k in s for k in ["industrial", "machinery", "aerospace", "transport", "logistics", "construction"]):
        return "Industrials"
    if any(k in s for k in ["real estate", "reit", "property"]):
        return "Real Estate"
    if any(k in s for k in ["telecom", "media", "communication"]):
        return "Communication"
    if "utilit" in s:
        return "Utilities"
    return "Other"


def _render_industry_kind_heatmap(nodes: pd.DataFrame) -> None:
    if nodes.empty:
        return

    work = nodes[["label", "liquidity"]].copy()
    work["kind"] = work["label"].map(_industry_kind)
    work = work.sort_values(["kind", "liquidity"], ascending=[True, False])
    work["rank_in_kind"] = work.groupby("kind").cumcount() + 1

    max_per_kind = 6
    work = work[work["rank_in_kind"] <= max_per_kind]
    if work.empty:
        return

    matrix = work.pivot(index="kind", columns="rank_in_kind", values="liquidity").fillna(0.0)
    matrix = matrix.sort_index()

    fig_h = max(2.4, len(matrix.index) * 0.48)
    fig, ax = plt.subplots(figsize=(10, fig_h))
    im = ax.imshow(matrix.values, aspect="auto", cmap="RdYlGn", vmin=-100, vmax=100)

    ax.set_yticks(range(len(matrix.index)))
    ax.set_yticklabels(matrix.index, fontsize=8)
    ax.set_xticks(range(len(matrix.columns)))
    ax.set_xticklabels([f"#{int(c)}" for c in matrix.columns], fontsize=8)
    ax.set_xlabel("Industry Rank in Kind (by Liquidity)", fontsize=8)
    ax.set_title("Industries Grouped by Kind (Liquidity Heatmap)", fontsize=10, pad=6)

    cbar = fig.colorbar(im, ax=ax, shrink=0.9)
    cbar.set_label("Liquidity (pts)", fontsize=8)
    cbar.ax.tick_params(labelsize=7)

    fig.tight_layout(pad=0.4)
    st.pyplot(fig)
    plt.close(fig)


def _render_flow_interpreter(nodes: pd.DataFrame, top_n: int = 5) -> None:
    """Render a plain-language flow breakdown for now vs recent days."""
    if nodes.empty:
        return

    # "Right now" uses short momentum; "Recent days" uses composite liquidity points.
    now_in = nodes.sort_values("ret_5", ascending=False).head(top_n).copy()
    now_out = nodes.sort_values("ret_5", ascending=True).head(top_n).copy()
    recent_in = nodes.sort_values("liquidity", ascending=False).head(top_n).copy()
    recent_out = nodes.sort_values("liquidity", ascending=True).head(top_n).copy()

    def _fmt_now(df: pd.DataFrame) -> pd.DataFrame:
        view = df[["label", "ticker", "bucket", "ret_5", "ret_20", "vol_jump"]].copy()
        view["ret_5_pct"] = view["ret_5"].map(lambda x: f"{float(x)*100:+.2f}%")
        view["ret_20_pct"] = view["ret_20"].map(lambda x: f"{float(x)*100:+.2f}%")
        view["volume_ratio"] = view["vol_jump"].map(lambda x: f"{float(x):.2f}")
        return view[["label", "ticker", "bucket", "ret_5_pct", "ret_20_pct", "volume_ratio"]]

    def _fmt_recent(df: pd.DataFrame) -> pd.DataFrame:
        view = df[["label", "ticker", "bucket", "liquidity", "ret_20", "vol_jump"]].copy()
        view["liquidity_pts"] = view["liquidity"].map(lambda x: f"{float(x):+.1f} pts")
        view["ret_20_pct"] = view["ret_20"].map(lambda x: f"{float(x)*100:+.2f}%")
        view["volume_ratio"] = view["vol_jump"].map(lambda x: f"{float(x):.2f}")
        return view[["label", "ticker", "bucket", "liquidity_pts", "ret_20_pct", "volume_ratio"]]

    st.markdown("**Liquidity Flow Interpreter**")
    st.caption(
        "Right now: 5-day relative move. Recent days: composite liquidity score (momentum + participation)."
    )

    now_out_col, now_in_col = st.columns(2)
    with now_out_col:
        st.markdown("**Money Removed Right Now (5D)**")
        st.dataframe(_fmt_now(now_out), use_container_width=True, hide_index=True)
    with now_in_col:
        st.markdown("**Money Invested Right Now (5D)**")
        st.dataframe(_fmt_now(now_in), use_container_width=True, hide_index=True)

    recent_out_col, recent_in_col = st.columns(2)
    with recent_out_col:
        st.markdown("**Money Removed in Recent Days**")
        st.dataframe(_fmt_recent(recent_out), use_container_width=True, hide_index=True)
    with recent_in_col:
        st.markdown("**Money Invested in Recent Days**")
        st.dataframe(_fmt_recent(recent_in), use_container_width=True, hide_index=True)

    bucket = nodes.groupby("bucket", as_index=False)[["liquidity", "ret_5"]].mean()
    bucket["liquidity_pts"] = bucket["liquidity"].map(lambda x: f"{float(x):+.1f} pts")
    bucket["ret_5_pct"] = bucket["ret_5"].map(lambda x: f"{float(x)*100:+.2f}%")
    bucket = bucket.sort_values("liquidity", ascending=False)

    st.markdown("**Net Flow by Bucket**")
    st.dataframe(bucket[["bucket", "liquidity_pts", "ret_5_pct"]], use_container_width=True, hide_index=True)


def _window_and_resample(series: pd.Series, months: int, frequency: str) -> pd.Series:
    s = _to_series(series)
    if s.empty:
        return pd.Series(dtype=float)
    if not isinstance(s.index, pd.DatetimeIndex):
        return pd.Series(dtype=float)

    s = s.sort_index()
    cutoff = s.index.max() - pd.DateOffset(months=months)
    s = s.loc[s.index >= cutoff]
    if s.empty:
        return pd.Series(dtype=float)

    if frequency == "Weekly":
        s = s.resample("W-FRI").sum().dropna()
    else:
        s = s.dropna()
    return s


def _series_trend_pct(series: pd.Series) -> float:
    if len(series) < 2:
        return 0.0
    first = float(series.iloc[0])
    last = float(series.iloc[-1])
    if first <= 0:
        return 0.0
    return (last / first - 1.0) * 100.0


def _collect_sector_volume_trends(
    universe: str,
    months: int,
    frequency: str,
    top_n: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    history: dict[str, pd.Series] = {}

    for sector in get_universe_sectors(universe):
        proxy = resolve_sector_proxy_ticker(universe, sector)
        if not proxy:
            continue
        df = fetch_sector_data(proxy, period="1y")
        if df.empty or "Close" not in df.columns or "Volume" not in df.columns:
            continue

        close = _to_series(df["Close"])
        volume = _to_series(df["Volume"])
        if close.empty or volume.empty:
            continue
        aligned_idx = close.index.intersection(volume.index)
        if len(aligned_idx) < 8:
            continue

        # Use dollar volume proxy to reflect likely money movement.
        dollar_volume = (close.loc[aligned_idx] * volume.loc[aligned_idx]).dropna()
        sampled = _window_and_resample(dollar_volume, months=months, frequency=frequency)
        if len(sampled) < 4:
            continue

        trend_pct = _series_trend_pct(sampled)
        rows.append(
            {
                "label": sector,
                "ticker": proxy,
                "trend_pct": trend_pct,
                "latest_flow_usd": float(sampled.iloc[-1]),
                "avg_flow_usd": float(sampled.mean()),
            }
        )
        history[sector] = sampled

    ranking = pd.DataFrame(rows)
    if ranking.empty:
        return ranking, pd.DataFrame()

    ranking = ranking.sort_values("trend_pct", ascending=False).reset_index(drop=True)
    leaders = ranking.head(top_n)["label"].tolist()
    history_df = pd.concat([history[k].rename(k) for k in leaders if k in history], axis=1)
    return ranking, history_df


def _collect_industry_volume_trends(
    universe: str,
    sector: str,
    months: int,
    frequency: str,
    top_n: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    history: dict[str, pd.Series] = {}

    counts = get_sector_industry_counts(universe, sector)
    for industry, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[: max(top_n * 2, 12)]:
        tickers = get_universe_tickers(universe, sector=sector, industry=industry)[:40]
        if len(tickers) < 2:
            continue

        _close, volume, fetched = compute_industry_aggregate(tickers)
        if fetched < 2:
            continue

        sampled = _window_and_resample(volume, months=months, frequency=frequency)
        if len(sampled) < 4:
            continue

        label = industry if industry != "undefined" else "Unclassified"
        trend_pct = _series_trend_pct(sampled)
        rows.append(
            {
                "label": label,
                "ticker": f"{fetched} stocks",
                "trend_pct": trend_pct,
                "latest_flow_shares": float(sampled.iloc[-1]),
                "avg_flow_shares": float(sampled.mean()),
            }
        )
        history[label] = sampled

    ranking = pd.DataFrame(rows)
    if ranking.empty:
        return ranking, pd.DataFrame()

    ranking = ranking.sort_values("trend_pct", ascending=False).reset_index(drop=True)
    leaders = ranking.head(top_n)["label"].tolist()
    history_df = pd.concat([history[k].rename(k) for k in leaders if k in history], axis=1)
    return ranking, history_df


def _format_billions(value: float) -> str:
    return f"${value / 1e9:,.2f}B"


def render_liquidity_chessboard(universe: str, selected_sector: str | None) -> None:
    st.subheader("Volume Trend Monitor")
    st.caption(
        "Simplified liquidity view: monitor where trading activity is trending for sectors and industries "
        "in the selected market."
    )

    conf_col_1, conf_col_2, conf_col_3 = st.columns([2, 2, 2])
    with conf_col_1:
        horizon = st.selectbox("Horizon", ["3 months", "6 months"], index=1, key="liq_trend_horizon")
    with conf_col_2:
        frequency = st.selectbox("Bars", ["Weekly", "Daily"], index=0, key="liq_trend_frequency")
    with conf_col_3:
        top_n = st.slider("Top Groups", 4, 12, 8, 1, key="liq_trend_top_n")

    months = 3 if horizon == "3 months" else 6

    sector_ranking, sector_history = _collect_sector_volume_trends(
        universe=universe,
        months=months,
        frequency=frequency,
        top_n=top_n,
    )

    st.markdown("**Sector Volume Trend (Dollar Volume Proxy)**")
    st.caption(
        f"Market: {universe}. Trend is computed from {frequency.lower()} bars over the last {months} months."
    )

    if sector_ranking.empty:
        st.info("Not enough sector proxy data to build volume trends.")
    else:
        sector_table = sector_ranking[["label", "ticker", "trend_pct", "latest_flow_usd", "avg_flow_usd"]].copy()
        sector_table["trend_pct"] = sector_table["trend_pct"].map(lambda x: f"{float(x):+.1f}%")
        sector_table["latest_flow_usd"] = sector_table["latest_flow_usd"].map(_format_billions)
        sector_table["avg_flow_usd"] = sector_table["avg_flow_usd"].map(_format_billions)
        st.dataframe(
            sector_table.rename(
                columns={
                    "label": "Sector",
                    "ticker": "Proxy",
                    "trend_pct": "Trend",
                    "latest_flow_usd": "Latest Flow",
                    "avg_flow_usd": "Average Flow",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
        if not sector_history.empty:
            st.bar_chart(sector_history, use_container_width=True)

    effective_sector = selected_sector
    if not effective_sector:
        sectors = get_universe_sectors(universe)
        effective_sector = sectors[0] if sectors else None

    if not effective_sector:
        st.info("No sector available to derive industry volume trends.")
        return

    st.markdown(f"**Industry Volume Trend ({effective_sector})**")
    st.caption("Industries are built from aggregated stock volumes in the selected sector.")

    industry_ranking, industry_history = _collect_industry_volume_trends(
        universe=universe,
        sector=effective_sector,
        months=months,
        frequency=frequency,
        top_n=top_n,
    )

    if industry_ranking.empty:
        st.info("Not enough industry data to build volume trends.")
        return

    industry_table = industry_ranking[["label", "ticker", "trend_pct", "latest_flow_shares", "avg_flow_shares"]].copy()
    industry_table["trend_pct"] = industry_table["trend_pct"].map(lambda x: f"{float(x):+.1f}%")
    industry_table["latest_flow_shares"] = industry_table["latest_flow_shares"].map(lambda x: f"{float(x):,.0f} shares")
    industry_table["avg_flow_shares"] = industry_table["avg_flow_shares"].map(lambda x: f"{float(x):,.0f} shares")

    st.dataframe(
        industry_table.rename(
            columns={
                "label": "Industry",
                "ticker": "Coverage",
                "trend_pct": "Trend",
                "latest_flow_shares": "Latest Flow",
                "avg_flow_shares": "Average Flow",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    if not industry_history.empty:
        st.bar_chart(industry_history, use_container_width=True)

def render_liquidity_chessboard(universe: str, selected_sector: str | None) -> None:
    st.subheader("Liquidity Chessboard (Spike)")
    st.caption(
        "Prototype: score squares from momentum + abnormal volume and infer possible rotation "
        "edges from weak buckets to strong buckets."
    )

    all_markets = st.checkbox(
        "Analyze all markets together",
        key="liquidity_all_markets",
        help="Combine all configured universes into one liquidity board.",
    )

    layer_options = ["Cross-Asset", "Markets", "Sectors"] if all_markets else ["Cross-Asset", "Markets", "Sectors", "Industries"]
    layer = st.selectbox(
        "Layer",
        layer_options,
        key="liquidity_layer",
        help="Switch between asset-class and equity hierarchy layers.",
    )

    if all_markets and layer == "Sectors":
        st.caption("Same sector names are aggregated across markets in combined mode.")

    conf_col_1, conf_col_2, conf_col_3, conf_col_4, conf_col_5 = st.columns([2, 2, 2, 2, 1])
    with conf_col_1:
        period = st.selectbox("Data Period", ["6mo", "1y", "2y", "5y"], index=1, key="liq_period")
    with conf_col_2:
        long_lookback = st.slider("Long Lookback (days)", 10, 126, 20, 1, key="liq_lb_long")
    with conf_col_3:
        short_lookback = st.slider("Short Lookback (days)", 3, 42, 5, 1, key="liq_lb_short")
    with conf_col_4:
        volume_base = st.slider("Volume Baseline (days)", 10, 120, 20, 1, key="liq_vol_base")
    with conf_col_5:
        edge_count = st.slider("Arrows", 1, 8, 5, 1, key="liq_edge_count")

    volume_recent = st.slider("Recent Volume Window (days)", 3, 20, 5, 1, key="liq_vol_recent")
    max_industries = st.slider("Max Industries in Industry Layer", 6, 20, 12, 1, key="liq_max_industries")

    if short_lookback >= long_lookback:
        short_lookback = max(3, long_lookback - 1)
        st.caption(f"Short lookback adjusted to {short_lookback} so it remains below long lookback.")

    effective_sector = selected_sector
    if layer == "Industries" and not effective_sector:
        sectors = get_universe_sectors(universe)
        effective_sector = sectors[0] if sectors else None
        if effective_sector:
            st.caption(f"Industry layer uses sector: {effective_sector}")

    nodes = get_liquidity_nodes(
        universe,
        effective_sector,
        layer,
        all_markets,
        period,
        long_lookback,
        short_lookback,
        volume_recent,
        volume_base,
        max_industries,
    )
    edges = build_flow_edges(nodes, max_edges=edge_count)
    regime = classify_liquidity_regime(nodes)
    sentiment = get_market_sentiment_snapshot(period=period)

    top_in = nodes.sort_values("liquidity", ascending=False).head(5)
    top_out = nodes.sort_values("liquidity", ascending=True).head(5)
    most_affected = (
        nodes.assign(
            impact_abs=nodes["liquidity"].abs(),
            direction=np.where(nodes["liquidity"] >= 0, "Receiving", "Losing"),
        )
        .sort_values("impact_abs", ascending=False)
        .head(10)
    )

    summary_left, summary_mid, summary_right, summary_vix, summary_fg = st.columns([1, 1, 1, 1, 1])
    with summary_left:
        st.metric("Regime", regime)
    with summary_mid:
        mean_liq = float(nodes["liquidity"].mean()) if not nodes.empty else 0.0
        st.metric("Board Mean", f"{mean_liq:+.1f} pts")
    with summary_right:
        dispersion = float(nodes["liquidity"].std(ddof=0)) if len(nodes) > 1 else 0.0
        st.metric("Dispersion", f"{dispersion:.1f} pts")
    with summary_vix:
        st.metric("VIX", f"{sentiment['vix']:.2f} pts", delta=f"{sentiment['vix_chg_20d_pct']:+.1f}% (20D)")
    with summary_fg:
        st.metric("Fear & Greed (proxy)", f"{sentiment['fear_greed']:.0f} pts", delta=str(sentiment["sentiment"]))

    st.caption(
        f"Current scoring horizon: {short_lookback}d short momentum + {long_lookback}d long momentum, "
        f"volume ratio {volume_recent}d / {volume_base}d baseline, source period {period}."
    )
    st.caption(
        "Sentiment uses cross-asset proxies (SPY, IWM, HYG/LQD, TLT, GLD, UUP) plus VIX; "
        "Fear & Greed is an internal model score, not the CNN proprietary index."
    )

    _render_chessboard(nodes, edges, f"{layer} Flow Board")

    _render_flow_interpreter(nodes, top_n=5)

    if layer == "Industries":
        _render_industry_kind_heatmap(nodes)

    table_col_left, table_col_right = st.columns(2)
    with table_col_left:
        st.markdown("**Top Inflows**")
        top_in_view = top_in[["label", "ticker", "liquidity", "ret_20"]].copy()
        top_in_view["liquidity_pts"] = top_in_view["liquidity"].map(lambda x: f"{float(x):+.1f} pts")
        top_in_view["return_lookback_pct"] = top_in_view["ret_20"].map(lambda x: f"{float(x)*100:+.1f}%")
        st.dataframe(top_in_view[["label", "ticker", "liquidity_pts", "return_lookback_pct"]], use_container_width=True, hide_index=True)
    with table_col_right:
        st.markdown("**Top Outflows**")
        top_out_view = top_out[["label", "ticker", "liquidity", "ret_20"]].copy()
        top_out_view["liquidity_pts"] = top_out_view["liquidity"].map(lambda x: f"{float(x):+.1f} pts")
        top_out_view["return_lookback_pct"] = top_out_view["ret_20"].map(lambda x: f"{float(x)*100:+.1f}%")
        st.dataframe(top_out_view[["label", "ticker", "liquidity_pts", "return_lookback_pct"]], use_container_width=True, hide_index=True)

    st.markdown("**Most Affected (Absolute Move)**")
    affected_view = most_affected[["label", "ticker", "bucket", "direction", "liquidity", "ret_20", "ret_5", "vol_jump"]].copy()
    affected_view["liquidity_pts"] = affected_view["liquidity"].map(lambda x: f"{float(x):+.1f} pts")
    affected_view["return_long_pct"] = affected_view["ret_20"].map(lambda x: f"{float(x)*100:+.1f}%")
    affected_view["return_short_pct"] = affected_view["ret_5"].map(lambda x: f"{float(x)*100:+.1f}%")
    affected_view["volume_ratio"] = affected_view["vol_jump"].map(lambda x: f"{float(x):.2f}")
    st.dataframe(
        affected_view[["label", "ticker", "bucket", "direction", "liquidity_pts", "return_long_pct", "return_short_pct", "volume_ratio"]],
        use_container_width=True,
        hide_index=True,
    )

    if all_markets and layer == "Sectors" and "market_count" in nodes.columns:
        st.markdown("**Aggregated Sector Breakdown (All Markets)**")
        breakdown = nodes[["label", "market_count", "liquidity", "ret_20", "ret_5", "vol_jump", "members"]].copy()
        breakdown["liquidity_pts"] = breakdown["liquidity"].map(lambda x: f"{float(x):+.1f} pts")
        breakdown["return_long_pct"] = breakdown["ret_20"].map(lambda x: f"{float(x)*100:+.1f}%")
        breakdown["return_short_pct"] = breakdown["ret_5"].map(lambda x: f"{float(x)*100:+.1f}%")
        breakdown["volume_ratio"] = breakdown["vol_jump"].map(lambda x: f"{float(x):.2f}")
        breakdown = breakdown.rename(
            columns={
                "label": "sector",
                "market_count": "markets_aggregated",
            }
        )
        st.dataframe(
            breakdown[["sector", "markets_aggregated", "liquidity_pts", "return_long_pct", "return_short_pct", "volume_ratio", "members"]],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("**Likely Rotation Paths**")
    if edges:
        edge_view = pd.DataFrame(edges)
        edge_view["magnitude_pts"] = edge_view["magnitude"].map(lambda x: f"{float(x):.1f} pts")
        st.dataframe(edge_view[["from", "to", "magnitude_pts"]], use_container_width=True, hide_index=True)
    else:
        st.caption("No strong rotation edges detected.")
