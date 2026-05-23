import pandas as pd
import yfinance as yf
import numpy as np

from ..data.data import (
    compute_industry_aggregate,
    fetch_sector_data,
    fetch_ticker_data_batch,
)
from ..data.universe import get_universe_tickers, load_universe


def as_series(values: pd.Series | pd.DataFrame | None) -> pd.Series:
    if isinstance(values, pd.Series):
        return pd.to_numeric(values, errors="coerce").dropna()
    if isinstance(values, pd.DataFrame):
        if values.empty:
            return pd.Series(dtype=float)
        numeric = values.apply(pd.to_numeric, errors="coerce")
        non_null_counts = numeric.notna().sum(axis=0)
        if non_null_counts.empty or int(non_null_counts.max()) == 0:
            return pd.Series(dtype=float)
        return numeric.loc[:, non_null_counts.idxmax()].dropna()
    return pd.Series(dtype=float)


def _latest_table_value(table: pd.DataFrame, row_name: str) -> float | None:
    if not isinstance(table, pd.DataFrame) or table.empty or row_name not in table.index:
        return None
    series = pd.to_numeric(table.loc[row_name], errors="coerce").dropna()
    if series.empty:
        return None
    return float(series.iloc[0])


def compute_return_vol_rr(close: pd.Series, lookback: int = 30) -> dict[str, float]:
    """Compute annualized expected return, volatility, and simple risk/reward ratio."""
    if close is None or close.empty:
        return {"exp_return_ann_pct": 0.0, "exp_vol_ann_pct": 0.0, "risk_reward": 0.0}

    series = close.dropna()
    if len(series) < max(lookback, 5):
        return {"exp_return_ann_pct": 0.0, "exp_vol_ann_pct": 0.0, "risk_reward": 0.0}

    rets = series.pct_change().dropna().tail(lookback)
    if rets.empty:
        return {"exp_return_ann_pct": 0.0, "exp_vol_ann_pct": 0.0, "risk_reward": 0.0}

    mean_daily = float(rets.mean())
    std_daily = float(rets.std(ddof=0))

    exp_return_ann_pct = mean_daily * 252 * 100
    exp_vol_ann_pct = std_daily * np.sqrt(252) * 100
    risk_reward = exp_return_ann_pct / exp_vol_ann_pct if exp_vol_ann_pct > 0 else 0.0

    return {
        "exp_return_ann_pct": exp_return_ann_pct,
        "exp_vol_ann_pct": exp_vol_ann_pct,
        "risk_reward": risk_reward,
    }


def compute_liquidity_context(close: pd.Series, volume: pd.Series) -> dict[str, float | str]:
    close = as_series(close)
    volume = as_series(volume)
    if close.empty or volume.empty:
        return {
            "liq_trend_3m_pct": 0.0,
            "liq_trend_6m_pct": 0.0,
            "liq_accel_weekly_pct": 0.0,
            "volume_ratio_20_60": 0.0,
            "liq_context": "No Signal",
        }

    aligned_idx = close.index.intersection(volume.index)
    if len(aligned_idx) < 20:
        return {
            "liq_trend_3m_pct": 0.0,
            "liq_trend_6m_pct": 0.0,
            "liq_accel_weekly_pct": 0.0,
            "volume_ratio_20_60": 0.0,
            "liq_context": "No Signal",
        }

    dollar_volume = (close.loc[aligned_idx] * volume.loc[aligned_idx]).dropna().sort_index()
    if len(dollar_volume) < 20:
        return {
            "liq_trend_3m_pct": 0.0,
            "liq_trend_6m_pct": 0.0,
            "liq_accel_weekly_pct": 0.0,
            "volume_ratio_20_60": 0.0,
            "liq_context": "No Signal",
        }

    def _trend_pct(series: pd.Series, bars: int) -> float:
        if len(series) < bars:
            return 0.0
        seg = series.tail(bars)
        first = float(seg.iloc[0])
        last = float(seg.iloc[-1])
        if first <= 0:
            return 0.0
        return (last / first - 1.0) * 100.0

    trend_3m = _trend_pct(dollar_volume, 63)
    trend_6m = _trend_pct(dollar_volume, 126)

    recent_20 = float(dollar_volume.tail(20).mean()) if len(dollar_volume) >= 20 else 0.0
    baseline_60 = float(dollar_volume.tail(80).head(60).mean()) if len(dollar_volume) >= 80 else 0.0
    volume_ratio = recent_20 / baseline_60 if baseline_60 > 0 else 0.0

    if isinstance(dollar_volume.index, pd.DatetimeIndex):
        weekly = dollar_volume.resample("W-FRI").sum().dropna()
    else:
        weekly = pd.Series(dtype=float)

    weekly_accel = 0.0
    if len(weekly) >= 9:
        recent_3w = float(weekly.tail(3).mean())
        base_6w = float(weekly.tail(9).head(6).mean())
        if base_6w > 0:
            weekly_accel = (recent_3w / base_6w - 1.0) * 100.0

    if trend_3m >= 20 and weekly_accel >= 5:
        context = "Rising Inflow"
    elif trend_3m <= -20 and weekly_accel <= -5:
        context = "Fading Interest"
    else:
        context = "Mixed / Stable"

    return {
        "liq_trend_3m_pct": float(trend_3m),
        "liq_trend_6m_pct": float(trend_6m),
        "liq_accel_weekly_pct": float(weekly_accel),
        "volume_ratio_20_60": float(volume_ratio),
        "liq_context": context,
    }


def macro_impact_snapshot(ticker: str) -> dict[str, str | float]:
    proxy_map = {
        "Risk (SPY)": "SPY",
        "Rates (TLT)": "TLT",
        "USD (UUP)": "UUP",
        "Gold (GLD)": "GLD",
        "Volatility (VIX)": "^VIX",
    }

    _, stock_df = fetch_ticker_data_batch(ticker, False)
    if stock_df.empty or "Close" not in stock_df.columns:
        return {
            "macro_context": "No Signal",
            "macro_driver": "N/A",
            "macro_beta_hint": "N/A",
            "macro_regime": "N/A",
        }

    stock_close = as_series(stock_df["Close"])
    stock_returns = stock_close.pct_change().dropna().tail(126)
    if len(stock_returns) < 20:
        return {
            "macro_context": "No Signal",
            "macro_driver": "N/A",
            "macro_beta_hint": "N/A",
            "macro_regime": "N/A",
        }

    correlations: dict[str, float] = {}
    for label, proxy in proxy_map.items():
        proxy_df = fetch_sector_data(proxy, period="1y")
        if proxy_df.empty or "Close" not in proxy_df.columns:
            continue
        proxy_close = as_series(proxy_df["Close"])
        proxy_returns = proxy_close.pct_change().dropna().tail(126)
        merged = pd.concat([stock_returns, proxy_returns], axis=1, join="inner").dropna()
        if len(merged) < 20:
            continue
        corr = float(merged.iloc[:, 0].corr(merged.iloc[:, 1]))
        if not pd.isna(corr):
            correlations[label] = corr

    if not correlations:
        return {
            "macro_context": "No Signal",
            "macro_driver": "N/A",
            "macro_beta_hint": "N/A",
            "macro_regime": "N/A",
        }

    top_driver = max(correlations.items(), key=lambda kv: abs(kv[1]))
    driver_label, corr_value = top_driver
    beta_hint = "Pro-cyclical" if corr_value > 0 else "Defensive / Hedge"

    if driver_label.startswith("Risk") and corr_value > 0.35:
        macro_context = "Risk-On Sensitive"
    elif driver_label.startswith("Rates") and corr_value > 0.30:
        macro_context = "Rates-Led"
    elif driver_label.startswith("USD") and abs(corr_value) > 0.30:
        macro_context = "USD-Sensitive"
    elif driver_label.startswith("Gold") and abs(corr_value) > 0.30:
        macro_context = "Inflation / Hedge"
    elif driver_label.startswith("Volatility") and corr_value < -0.30:
        macro_context = "Volatility Inverse"
    else:
        macro_context = "Mixed Macro"

    spy_df = fetch_sector_data("SPY", period="1y")
    tlt_df = fetch_sector_data("TLT", period="1y")
    spy_close = as_series(spy_df["Close"]) if "Close" in spy_df.columns else pd.Series(dtype=float)
    tlt_close = as_series(tlt_df["Close"]) if "Close" in tlt_df.columns else pd.Series(dtype=float)
    spy_3m = float((spy_close.iloc[-1] / spy_close.iloc[-63] - 1.0) * 100.0) if len(spy_close) >= 63 else 0.0
    tlt_3m = float((tlt_close.iloc[-1] / tlt_close.iloc[-63] - 1.0) * 100.0) if len(tlt_close) >= 63 else 0.0
    regime = "Risk-On" if spy_3m >= 0 and tlt_3m <= 0 else "Risk-Off / Cautious"

    return {
        "macro_context": macro_context,
        "macro_driver": f"{driver_label} corr {corr_value:+.2f}",
        "macro_beta_hint": beta_hint,
        "macro_regime": regime,
    }


def news_topic(title: str) -> str:
    text = (title or "").lower()
    if any(word in text for word in ["election", "tariff", "sanction", "government", "parliament", "policy"]):
        return "Politics"
    if any(word in text for word in ["inflation", "recession", "gdp", "rate cut", "rate hike", "economy", "jobs"]):
        return "Economy"
    if any(word in text for word in ["upgrade", "downgrade", "target price", "analyst", "rating", "broker"]):
        return "Rating"
    return "General"


def recent_info_snapshot(
    universe: str,
    ticker: str,
    ticker_factory=yf.Ticker,
) -> dict[str, object]:
    fallback = {
        "rating_label": "N/A",
        "rating_detail": "No analyst snapshot",
        "mrsi_pct": 0.0,
        "mrsi_label": "No Signal",
        "industry_name": "N/A",
        "news_items": [],
    }

    try:
        stock = ticker_factory(ticker)
    except Exception:
        return fallback

    info = {}
    try:
        info = stock.info or {}
    except Exception:
        info = {}

    rating_key = str(info.get("recommendationKey") or "").strip().lower()
    analyst_count = info.get("numberOfAnalystOpinions")
    target_price = info.get("targetMeanPrice")
    rating_label_map = {
        "strong_buy": "Strong Buy",
        "buy": "Buy",
        "hold": "Hold",
        "underperform": "Underperform",
        "sell": "Sell",
    }
    rating_label = rating_label_map.get(rating_key, "N/A") if rating_key else "N/A"
    rating_detail_parts = []
    if analyst_count is not None:
        rating_detail_parts.append(f"{int(analyst_count)} analysts")
    if target_price is not None:
        rating_detail_parts.append(f"target ${float(target_price):.2f}")
    rating_detail = " · ".join(rating_detail_parts) if rating_detail_parts else "No analyst snapshot"

    news_items: list[dict[str, str]] = []
    try:
        raw_news = getattr(stock, "news", []) or []
        for item in raw_news[:3]:
            content = item.get("content", {}) if isinstance(item, dict) else {}
            title = str(content.get("title") or item.get("title") or "").strip()
            provider = str(content.get("provider", {}).get("displayName") or item.get("publisher") or "").strip()
            if not title:
                continue
            news_items.append(
                {
                    "topic": news_topic(title),
                    "title": title,
                    "provider": provider or "News",
                }
            )
    except Exception:
        news_items = []

    universe_df = load_universe(universe)
    row = universe_df.loc[universe_df["Ticker"] == ticker]
    if row.empty:
        return {
            **fallback,
            "rating_label": rating_label,
            "rating_detail": rating_detail,
            "news_items": news_items,
        }

    sector = str(row.iloc[0]["Sector"])
    industry = str(row.iloc[0]["Industry"])
    peers = [peer for peer in get_universe_tickers(universe, sector=sector, industry=industry) if peer != ticker][:25]
    if len(peers) < 2:
        return {
            **fallback,
            "rating_label": rating_label,
            "rating_detail": rating_detail,
            "industry_name": industry or "N/A",
            "news_items": news_items,
        }

    _, stock_df = fetch_ticker_data_batch(ticker, False)
    stock_close = as_series(stock_df["Close"]) if (not stock_df.empty and "Close" in stock_df.columns) else pd.Series(dtype=float)
    industry_close, _industry_volume, fetched = compute_industry_aggregate(peers)
    industry_close = as_series(industry_close)

    mrsi_pct = 0.0
    if len(stock_close) >= 63 and len(industry_close) >= 63 and fetched >= 2:
        stock_ret = float(stock_close.iloc[-1] / stock_close.iloc[-63] - 1.0)
        industry_ret = float(industry_close.iloc[-1] / industry_close.iloc[-63] - 1.0)
        mrsi_pct = (stock_ret - industry_ret) * 100.0

    if mrsi_pct >= 8:
        mrsi_label = "Clear Outperformer"
    elif mrsi_pct >= 2:
        mrsi_label = "Beating Industry"
    elif mrsi_pct <= -8:
        mrsi_label = "Clear Laggard"
    elif mrsi_pct <= -2:
        mrsi_label = "Lagging Industry"
    else:
        mrsi_label = "In Line"

    return {
        "rating_label": rating_label,
        "rating_detail": rating_detail,
        "mrsi_pct": float(mrsi_pct),
        "mrsi_label": mrsi_label,
        "industry_name": industry or "N/A",
        "news_items": news_items,
    }


def stock_classification(universe: str, ticker: str) -> dict[str, str]:
    df = load_universe(universe)
    row = df.loc[df["Ticker"] == ticker]
    if row.empty:
        return {"sector": "N/A", "industry": "N/A"}
    return {
        "sector": str(row.iloc[0]["Sector"] or "N/A"),
        "industry": str(row.iloc[0]["Industry"] or "N/A"),
    }


def compute_stock_metrics(df: pd.DataFrame, ticker: str, ticker_factory=yf.Ticker) -> dict:
    """Compute key metrics for a stock including technicals and fundamentals."""
    metrics = {}

    if not df.empty and "Close" in df.columns:
        close = as_series(df["Close"])
        if close.empty:
            close = pd.Series(dtype=float)
    else:
        close = pd.Series(dtype=float)

    if not close.empty:
        latest = float(close.iloc[-1])
        prev_close = float(close.iloc[-20]) if len(close) > 20 else float(close.iloc[0])
        change_pct = ((latest - prev_close) / prev_close * 100) if prev_close > 0 else 0

        ma50 = float(close.rolling(50).mean().iloc[-1])
        ma150 = float(close.rolling(150).mean().iloc[-1])

        vol_20 = float(close.pct_change().tail(20).std() * 100) if len(close) > 20 else 0

        metrics.update({
            "latest": latest,
            "change_20d_pct": change_pct,
            "ma50": ma50,
            "ma150": ma150,
            "volatility_20d": vol_20,
        })

        risk_metrics = compute_return_vol_rr(close, lookback=30)
        metrics.update(risk_metrics)

        if "Volume" in df.columns:
            liquidity_context = compute_liquidity_context(close, df["Volume"])
            metrics.update(liquidity_context)

    try:
        tick = ticker_factory(ticker)
        info = tick.info or {}

        metrics.update({
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "dividend_yield": info.get("dividendYield"),
            "pb_ratio": info.get("priceToBook"),
            "ps_ratio": info.get("priceToSalesTrailing12Months"),
            "peg_ratio": info.get("pegRatio"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "revenue_growth_yoy": info.get("revenueGrowth"),
            "earnings_growth_yoy": info.get("earningsGrowth"),
            "beta": info.get("beta"),
            "debt_to_equity": info.get("debtToEquity"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "eps_trailing": info.get("trailingEps"),
            "eps_forward": info.get("forwardEps"),
            "dividend_per_share": info.get("dividendRate"),
        })

        revenue_ttm = info.get("totalRevenue")
        free_cash_flow = info.get("freeCashflow")

        try:
            financials = tick.financials
            balance_sheet = tick.balance_sheet
            cashflow = tick.cashflow

            total_revenue = _latest_table_value(financials, "Total Revenue")
            gross_profit = _latest_table_value(financials, "Gross Profit")
            operating_income = _latest_table_value(financials, "Operating Income")
            ebit = _latest_table_value(financials, "EBIT")
            total_assets = _latest_table_value(balance_sheet, "Total Assets")
            current_liabilities = _latest_table_value(balance_sheet, "Current Liabilities")
            free_cash_flow = _latest_table_value(cashflow, "Free Cash Flow") or free_cash_flow

            if total_revenue is not None:
                revenue_ttm = total_revenue

            gross_margin = None
            operating_margin = None
            if total_revenue and total_revenue > 0:
                if gross_profit is not None:
                    gross_margin = gross_profit / total_revenue * 100.0
                if operating_income is not None:
                    operating_margin = operating_income / total_revenue * 100.0

            roce = None
            if ebit is not None and total_assets is not None and current_liabilities is not None:
                capital_employed = total_assets - current_liabilities
                if capital_employed:
                    roce = ebit / capital_employed * 100.0

            metrics.update({
                "gross_margin": gross_margin,
                "operating_margin": operating_margin,
                "roce": roce,
                "free_cash_flow": free_cash_flow,
                "revenue_ttm": revenue_ttm,
            })
        except Exception:
            metrics.update({
                "gross_margin": None,
                "operating_margin": None,
                "roce": None,
                "free_cash_flow": free_cash_flow,
                "revenue_ttm": revenue_ttm,
            })

        fcf_margin = None
        if free_cash_flow is not None and revenue_ttm:
            try:
                fcf_margin = float(free_cash_flow) / float(revenue_ttm) * 100.0
            except Exception:
                fcf_margin = None

        fcf_yield = None
        if free_cash_flow is not None and info.get("marketCap"):
            try:
                fcf_yield = float(free_cash_flow) / float(info.get("marketCap")) * 100.0
            except Exception:
                fcf_yield = None

        metrics.update({
            "fcf_margin": fcf_margin,
            "fcf_yield": fcf_yield,
        })

        try:
            earnings_dates = tick.quarterly_financials
            if not earnings_dates.empty:
                latest_earnings_date = earnings_dates.columns[0]
                metrics["latest_earnings_date"] = latest_earnings_date
        except Exception:
            pass

    except Exception:
        pass

    return metrics
