import pandas as pd
import yfinance as yf
from financedatabase import Equities
from ..constants import (
    DEFAULT_TOP_TICKERS,
    INDEX_START_VALUE,
    SECTOR_NAME_MAP,
    TICKER_PERIOD,
)
from .cache import load_ticker_from_cache, save_ticker_to_cache, clear_ticker_cache
from .cache import get_ticker_cache_age_seconds, load_ticker_from_cache_any_age
from .cache import (
    clear_ticker_unavailable_flag,
    get_ticker_unavailable_retry_after_seconds,
    is_ticker_temporarily_unavailable,
    mark_ticker_temporarily_unavailable,
)
from .download_status import (
    is_download_blocked,
    record_download_failure,
    record_download_success,
)


UNAVAILABLE_TICKER_COOLDOWN_SECONDS = 6 * 60 * 60


def get_db_sector_name(sector: str) -> str:
    return SECTOR_NAME_MAP.get(sector, sector)


def load_equities() -> Equities:
    return Equities()


def _normalize_tickers(tickers: list[str]) -> list[str]:
    normalized = [str(t).strip() for t in tickers if str(t).strip()]
    return list(dict.fromkeys(normalized))


def _download_market_data_batch(tickers: list[str], period: str) -> dict[str, pd.DataFrame]:
    """Download market data from yfinance for one or many symbols."""
    ordered = _normalize_tickers(tickers)
    if not ordered:
        return {}

    if is_download_blocked("yfinance"):
        return {ticker: pd.DataFrame() for ticker in ordered}

    try:
        if len(ordered) == 1:
            ticker = ordered[0]
            df = yf.download(ticker, period=period, progress=False)
            if df is not None and not df.empty:
                record_download_success(source="yfinance")
                return {ticker: df}
            return {ticker: pd.DataFrame()}

        batch = yf.download(
            tickers=" ".join(ordered),
            period=period,
            progress=False,
            group_by="ticker",
            threads=True,
        )
    except Exception as exc:
        record_download_failure(exc, source="yfinance")
        return {ticker: pd.DataFrame() for ticker in ordered}

    if batch is None or batch.empty:
        return {ticker: pd.DataFrame() for ticker in ordered}

    results: dict[str, pd.DataFrame] = {ticker: pd.DataFrame() for ticker in ordered}
    if isinstance(batch.columns, pd.MultiIndex):
        top_level = set(batch.columns.get_level_values(0))
        for ticker in ordered:
            if ticker not in top_level:
                continue
            df = batch[ticker].dropna(how="all")
            if not df.empty:
                results[ticker] = df

    if any(not frame.empty for frame in results.values()):
        record_download_success(source="yfinance")

    return results


def _format_data_freshness_label(source: str, age_seconds: int | None = None) -> str:
    if source == "live":
        return "Live (up to date)"
    if source == "cache_fresh":
        if age_seconds is None:
            return "Cached"
        mins = max(1, int(age_seconds // 60))
        return f"Cached ({mins} min old)"
    if source == "cache_stale":
        if age_seconds is None:
            return "Cached (out of date)"
        hours = max(1, int(age_seconds // 3600))
        return f"Cached (out of date, {hours}h old)"
    if source == "unavailable_cooldown":
        if age_seconds is None:
            return "Temporarily unavailable (cooldown)"
        mins = max(1, int(age_seconds // 60))
        return f"Temporarily unavailable (retry in about {mins} min)"
    return "No data"


def _fetch_market_data_bundle(
    tickers: list[str],
    period: str = TICKER_PERIOD,
    force_refresh: bool = False,
    use_cache: bool = True,
    allow_stale_cache_fallback: bool = True,
) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, object]]]:
    ordered = _normalize_tickers(tickers)
    if not ordered:
        return {}, {}

    cache_enabled = use_cache and period == TICKER_PERIOD
    blocked = is_download_blocked("yfinance")
    results: dict[str, pd.DataFrame] = {}
    status_map: dict[str, dict[str, object]] = {}
    missing: list[str] = []

    for ticker in ordered:
        if is_ticker_temporarily_unavailable(ticker):
            retry_after = get_ticker_unavailable_retry_after_seconds(ticker)
            results[ticker] = pd.DataFrame()
            status_map[ticker] = {
                "source": "unavailable_cooldown",
                "is_stale": False,
                "age_seconds": retry_after,
                "label": _format_data_freshness_label("unavailable_cooldown", retry_after),
            }
            continue

        if cache_enabled and not force_refresh:
            cached = load_ticker_from_cache(ticker)
            if cached is not None and not cached.empty:
                age_seconds = get_ticker_cache_age_seconds(ticker)
                results[ticker] = cached
                status_map[ticker] = {
                    "source": "cache_fresh",
                    "is_stale": False,
                    "age_seconds": age_seconds,
                    "label": _format_data_freshness_label("cache_fresh", age_seconds),
                }
                continue
        missing.append(ticker)

    if missing:
        downloaded = _download_market_data_batch(missing, period=period)
        for ticker, df in downloaded.items():
            results[ticker] = df
            if df is not None and not df.empty:
                clear_ticker_unavailable_flag(ticker)
                status_map[ticker] = {
                    "source": "live",
                    "is_stale": False,
                    "age_seconds": 0,
                    "label": _format_data_freshness_label("live", 0),
                }
                if cache_enabled:
                    save_ticker_to_cache(ticker, df)

        unresolved = [ticker for ticker in missing if results.get(ticker, pd.DataFrame()).empty]
        for ticker in unresolved:
            single = _download_market_data_batch([ticker], period=period)
            df = single.get(ticker, pd.DataFrame())
            results[ticker] = df
            if df is not None and not df.empty:
                clear_ticker_unavailable_flag(ticker)
                status_map[ticker] = {
                    "source": "live",
                    "is_stale": False,
                    "age_seconds": 0,
                    "label": _format_data_freshness_label("live", 0),
                }
                if cache_enabled:
                    save_ticker_to_cache(ticker, df)
            elif not is_download_blocked("yfinance"):
                mark_ticker_temporarily_unavailable(
                    ticker,
                    reason="No data returned after batch and single-symbol retries.",
                    cooldown_seconds=UNAVAILABLE_TICKER_COOLDOWN_SECONDS,
                )
                retry_after = get_ticker_unavailable_retry_after_seconds(ticker)
                status_map[ticker] = {
                    "source": "unavailable_cooldown",
                    "is_stale": False,
                    "age_seconds": retry_after,
                    "label": _format_data_freshness_label("unavailable_cooldown", retry_after),
                }

    if cache_enabled and allow_stale_cache_fallback and blocked:
        for ticker in ordered:
            if ticker in status_map:
                continue
            stale = load_ticker_from_cache_any_age(ticker)
            if stale is None or stale.empty:
                continue
            age_seconds = get_ticker_cache_age_seconds(ticker)
            results[ticker] = stale
            status_map[ticker] = {
                "source": "cache_stale",
                "is_stale": True,
                "age_seconds": age_seconds,
                "label": _format_data_freshness_label("cache_stale", age_seconds),
            }

    for ticker in ordered:
        results.setdefault(ticker, pd.DataFrame())
        status_map.setdefault(
            ticker,
            {
                "source": "empty",
                "is_stale": False,
                "age_seconds": None,
                "label": _format_data_freshness_label("empty", None),
            },
        )

    return results, status_map


def fetch_market_data(
    tickers: list[str],
    period: str = TICKER_PERIOD,
    force_refresh: bool = False,
    use_cache: bool = True,
) -> dict[str, pd.DataFrame]:
    """Unified stock/ETF market-data pipeline with cache + yfinance fallback."""
    results, _status = _fetch_market_data_bundle(
        tickers,
        period=period,
        force_refresh=force_refresh,
        use_cache=use_cache,
        allow_stale_cache_fallback=True,
    )
    return results


def fetch_market_data_with_status(
    tickers: list[str],
    period: str = TICKER_PERIOD,
    force_refresh: bool = False,
    use_cache: bool = True,
    allow_stale_cache_fallback: bool = True,
) -> tuple[dict[str, pd.DataFrame], dict[str, dict[str, object]]]:
    """Unified market-data pipeline returning both data and freshness metadata."""
    return _fetch_market_data_bundle(
        tickers,
        period=period,
        force_refresh=force_refresh,
        use_cache=use_cache,
        allow_stale_cache_fallback=allow_stale_cache_fallback,
    )


def fetch_sector_data(ticker: str, period: str = TICKER_PERIOD) -> pd.DataFrame:
    return fetch_market_data([ticker], period=period, force_refresh=False, use_cache=(period == TICKER_PERIOD)).get(
        ticker, pd.DataFrame()
    )


def fetch_sector_industries(sector: str) -> pd.Series:
    db_sector = get_db_sector_name(sector)
    equities = load_equities()
    industries = equities.options("industry", sector=db_sector)
    return pd.Series(sorted(industries.tolist()), name="industry")


def fetch_industry_counts(sector: str) -> pd.Series:
    db_sector = get_db_sector_name(sector)
    equities = load_equities()
    selected = equities.select(sector=db_sector, exclude_exchanges=False)
    return selected["industry"].dropna().value_counts().sort_values(ascending=False)


def validate_ticker(ticker: str) -> bool:
    df = fetch_market_data([ticker], period="1d", force_refresh=True, use_cache=False).get(ticker, pd.DataFrame())
    return not df.empty and "Close" in df.columns


def fetch_industry_tickers(sector: str, industry: str, top_n: int = DEFAULT_TOP_TICKERS) -> list[str]:
    db_sector = get_db_sector_name(sector)
    equities = load_equities()
    selected = equities.select(sector=db_sector, industry=industry, exclude_exchanges=False)

    # Defensive: ensure selected is a DataFrame
    if not hasattr(selected, 'index'):
        return []

    if "market_cap" in selected.columns:
        selected = selected.sort_values("market_cap", ascending=False)

    valid_tickers = []
    for ticker in selected.index:
        cached = load_ticker_from_cache(ticker)
        if cached is not None and not cached.empty:
            valid_tickers.append(ticker)
            if len(valid_tickers) >= top_n:
                break

    return valid_tickers


def fetch_industry_stock_list(sector: str, industry: str) -> list[str]:
    db_sector = get_db_sector_name(sector)
    equities = load_equities()
    selected = equities.select(sector=db_sector, industry=industry, exclude_exchanges=False)

    # Defensive: ensure selected is a DataFrame
    if not hasattr(selected, 'index'):
        return []

    if "market_cap" in selected.columns:
        selected = selected.sort_values("market_cap", ascending=False)

    return [ticker for ticker in selected.index if (load_ticker_from_cache(ticker) is not None and not load_ticker_from_cache(ticker).empty)]


def compute_industry_aggregate(tickers: list[str]) -> tuple[pd.Series, pd.Series, int]:
    if not tickers:
        return pd.Series(), pd.Series(), 0

    ticker_frames = fetch_ticker_data_batch_many(tickers, force_refresh=False)

    closes = []
    volumes = []
    for ticker in tickers:
        df = ticker_frames.get(ticker, pd.DataFrame())
        if df is not None and not df.empty and "Close" in df.columns and "Volume" in df.columns:
            ticker_close = df["Close"]
            ticker_volume = df["Volume"]
            if not ticker_close.empty:
                closes.append(ticker_close)
                volumes.append(ticker_volume)

    num_fetched = len(closes)
    if num_fetched == 0:
        return pd.Series(), pd.Series(), 0

    close_df = pd.concat(closes, axis=1, keys=[f"ticker_{i}" for i in range(num_fetched)]).ffill().dropna(axis=0, how="all")
    volume_df = pd.concat(volumes, axis=1, keys=[f"ticker_{i}" for i in range(num_fetched)]).fillna(0)

    pct_changes = close_df.pct_change().mean(axis=1, skipna=True)
    index = (1 + pct_changes).cumprod() * INDEX_START_VALUE
    total_volume = volume_df.sum(axis=1)

    return index, total_volume, num_fetched


def validate_ticker_batch(ticker: str) -> tuple[str, bool]:
    df = fetch_market_data([ticker], period="1d", force_refresh=True, use_cache=False).get(ticker, pd.DataFrame())
    is_valid = not df.empty and "Close" in df.columns
    return ticker, is_valid


def fetch_ticker_data_batch(ticker: str, force_refresh: bool = False) -> tuple[str, pd.DataFrame]:
    """
    Fetch ticker data, using cache unless force_refresh is True.
    """
    df = fetch_market_data([ticker], period=TICKER_PERIOD, force_refresh=force_refresh, use_cache=True).get(
        ticker, pd.DataFrame()
    )
    return ticker, df


def fetch_ticker_data_batch_many(tickers: list[str], force_refresh: bool = False) -> dict[str, pd.DataFrame]:
    """Fetch many tickers efficiently, using cache and batch download for misses."""
    return fetch_market_data(tickers, period=TICKER_PERIOD, force_refresh=force_refresh, use_cache=True)
