"""CopyTrading rendering for a public-disclosure activity feed."""

from datetime import date, datetime, timedelta
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st


_ACTIVITY_TEMPLATES: list[dict[str, object]] = [
    {
        "actor": "Berkshire Hathaway",
        "actor_type": "Fund",
        "ticker": "OXY",
        "action": "Add",
        "days_ago": 12,
        "source": "SEC 13F filing",
        "source_url": "https://www.sec.gov/edgar/search/#/ciks=0001067983",
        "notes": "Position increase reported in a quarterly filing.",
    },
    {
        "actor": "Bridgewater Associates",
        "actor_type": "Fund",
        "ticker": "SPY",
        "action": "Increase",
        "days_ago": 21,
        "source": "SEC 13F filing",
        "source_url": "https://www.sec.gov/edgar/search/#/ciks=0001350694",
        "notes": "Broad market ETF exposure was raised.",
    },
    {
        "actor": "Pershing Square",
        "actor_type": "Fund",
        "ticker": "GOOGL",
        "action": "New",
        "days_ago": 38,
        "source": "Investor letter / filing",
        "source_url": "https://www.pershingsquareholdings.com/",
        "notes": "New long allocation disclosed publicly.",
    },
    {
        "actor": "Michael Burry",
        "actor_type": "Private Investor",
        "ticker": "JD",
        "action": "Add",
        "days_ago": 19,
        "source": "SEC 13F filing",
        "source_url": "https://www.sec.gov/edgar/search/#/ciks=0001649339",
        "notes": "Reported increase in China-linked holdings.",
    },
    {
        "actor": "Bill Ackman",
        "actor_type": "Private Investor",
        "ticker": "HLT",
        "action": "Trim",
        "days_ago": 45,
        "source": "Investor update",
        "source_url": "https://pershingsquare.com/",
        "notes": "Partial reduction disclosed in public commentary.",
    },
    {
        "actor": "Nancy Pelosi",
        "actor_type": "US Politician (Public filings)",
        "ticker": "NVDA",
        "action": "Call options",
        "days_ago": 9,
        "source": "Congressional transaction report",
        "source_url": "https://disclosures-clerk.house.gov/PublicDisclosure/FinancialDisclosure",
        "notes": "Trade appears in publicly filed periodic transaction disclosure.",
    },
    {
        "actor": "Dan Crenshaw",
        "actor_type": "US Politician (Public filings)",
        "ticker": "AAPL",
        "action": "Buy",
        "days_ago": 27,
        "source": "Congressional transaction report",
        "source_url": "https://disclosures-clerk.house.gov/PublicDisclosure/FinancialDisclosure",
        "notes": "Reported equity purchase in required filing window.",
    },
    {
        "actor": "Tommy Tuberville",
        "actor_type": "US Politician (Public filings)",
        "ticker": "MSFT",
        "action": "Sell",
        "days_ago": 66,
        "source": "Congressional transaction report",
        "source_url": "https://efdsearch.senate.gov/search/",
        "notes": "Sale recorded in public periodic transaction report.",
    },
]

_TRACKED_13F_CIKS: list[tuple[str, str, str]] = [
    ("0001067983", "Berkshire Hathaway", "Fund"),
    ("0001350694", "Bridgewater Associates", "Fund"),
    ("0001336528", "Pershing Square", "Fund"),
    ("0001649339", "Scion Asset Management", "Private Investor"),
]

_CONGRESS_FEED_URLS: list[str] = [
    "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json",
    "https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com/aggregate/all_transactions.json",
]

_HTTP_HEADERS = {
    "User-Agent": "sector-rotation-cop-trading/1.0 (public-disclosure-research)",
    "Accept": "application/json",
}


def _json_get(url: str, timeout_seconds: int = 15) -> object | None:
    try:
        req = Request(url, headers=_HTTP_HEADERS)
        with urlopen(req, timeout=timeout_seconds) as response:
            payload = response.read().decode("utf-8")
        return json.loads(payload)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None


def _parse_date(raw: object) -> date | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if "T" in text:
        text = text.split("T", maxsplit=1)[0]
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_sec_13f_activities() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for cik, actor, actor_type in _TRACKED_13F_CIKS:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        payload = _json_get(url)
        if not isinstance(payload, dict):
            continue

        filings = payload.get("filings", {})
        recent = filings.get("recent", {}) if isinstance(filings, dict) else {}
        forms = recent.get("form", []) if isinstance(recent, dict) else []
        filing_dates = recent.get("filingDate", []) if isinstance(recent, dict) else []
        accession_numbers = recent.get("accessionNumber", []) if isinstance(recent, dict) else []
        primary_documents = recent.get("primaryDocument", []) if isinstance(recent, dict) else []

        for idx, form in enumerate(forms):
            if form not in {"13F-HR", "13F-HR/A"}:
                continue
            filing_date = _parse_date(filing_dates[idx] if idx < len(filing_dates) else None)
            if filing_date is None:
                continue

            accession = str(accession_numbers[idx]) if idx < len(accession_numbers) else ""
            accession_nodash = accession.replace("-", "")
            primary_doc = str(primary_documents[idx]) if idx < len(primary_documents) else ""
            sec_filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_nodash}/{primary_doc}"
                if accession_nodash and primary_doc
                else f"https://www.sec.gov/edgar/search/#/ciks={cik}"
            )

            rows.append(
                {
                    "actor": actor,
                    "actor_type": actor_type,
                    "ticker": "",
                    "action": form,
                    "reported_on": filing_date,
                    "source": "SEC EDGAR",
                    "source_url": sec_filing_url,
                    "notes": f"Latest 13F filing detected for {actor}.",
                }
            )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_congress_activities() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for url in _CONGRESS_FEED_URLS:
        payload = _json_get(url)
        if not isinstance(payload, list):
            continue

        for entry in payload:
            if not isinstance(entry, dict):
                continue
            reported_on = _parse_date(
                entry.get("disclosure_date")
                or entry.get("disclosed_at")
                or entry.get("transaction_date")
                or entry.get("date")
            )
            if reported_on is None:
                continue

            actor = str(
                entry.get("representative")
                or entry.get("senator")
                or entry.get("politician")
                or entry.get("name")
                or "Unknown"
            )
            ticker = str(entry.get("ticker") or "").upper()
            if ticker in {"--", "N/A", "NONE"}:
                ticker = ""

            action = str(
                entry.get("transaction")
                or entry.get("type")
                or entry.get("action")
                or "Report"
            )
            amount = str(entry.get("amount") or "").strip()
            owner = str(entry.get("owner") or entry.get("owner_type") or "").strip()
            notes_parts = [part for part in [amount, owner] if part]
            notes = " | ".join(notes_parts) if notes_parts else "Public congressional transaction disclosure."

            rows.append(
                {
                    "actor": actor,
                    "actor_type": "US Politician (Public filings)",
                    "ticker": ticker,
                    "action": action,
                    "reported_on": reported_on,
                    "source": "Congressional transaction report",
                    "source_url": url,
                    "notes": notes,
                }
            )

    if not rows:
        return pd.DataFrame()

    deduped = pd.DataFrame(rows).drop_duplicates(subset=["actor", "ticker", "action", "reported_on", "source"])
    return deduped


def _sample_activities(today: date | None = None) -> pd.DataFrame:
    as_of = today or date.today()
    rows: list[dict[str, object]] = []
    for template in _ACTIVITY_TEMPLATES:
        reported_on = as_of - timedelta(days=int(template["days_ago"]))
        rows.append(
            {
                "actor": str(template["actor"]),
                "actor_type": str(template["actor_type"]),
                "ticker": str(template["ticker"]),
                "action": str(template["action"]),
                "reported_on": reported_on,
                "source": str(template["source"]),
                "source_url": str(template["source_url"]),
                "notes": str(template["notes"]),
            }
        )
    return pd.DataFrame(rows)


def get_copy_trading_activity(today: date | None = None) -> pd.DataFrame:
    """Return baseline sample activities enriched with live public-disclosure updates."""
    baseline = _sample_activities(today=today)
    frames: list[pd.DataFrame] = [baseline, _fetch_sec_13f_activities(), _fetch_congress_activities()]
    available = [frame for frame in frames if not frame.empty]

    result = pd.concat(available, ignore_index=True)

    required_columns = ["actor", "actor_type", "ticker", "action", "reported_on", "source", "source_url", "notes"]
    for column in required_columns:
        if column not in result.columns:
            result[column] = "" if column != "reported_on" else pd.NaT

    result["reported_on"] = pd.to_datetime(result["reported_on"], errors="coerce").dt.date
    result = result.dropna(subset=["reported_on"])
    result = result.drop_duplicates(subset=["actor", "ticker", "action", "reported_on", "source"], keep="first")
    return result[required_columns].sort_values("reported_on", ascending=False).reset_index(drop=True)


def filter_copy_trading_activity(
    activities: pd.DataFrame,
    actor_types: list[str],
    lookback_days: int,
    query: str,
) -> pd.DataFrame:
    """Apply activity-type, lookback, and text filters."""
    if activities.empty:
        return activities

    filtered = activities.copy()
    if actor_types:
        filtered = filtered[filtered["actor_type"].isin(actor_types)]

    cutoff = date.today() - timedelta(days=lookback_days)
    filtered = filtered[filtered["reported_on"] >= cutoff]

    q = query.strip().lower()
    if q:
        searchable = filtered[["actor", "ticker", "action", "notes", "source", "source_url"]].astype(str).agg(" ".join, axis=1)
        filtered = filtered[searchable.str.lower().str.contains(q, na=False)]

    return filtered.sort_values("reported_on", ascending=False).reset_index(drop=True)


def _watchlist_alerts(filtered: pd.DataFrame, watchlist_tickers: list[str], alert_window_days: int) -> tuple[int, pd.DataFrame]:
    if filtered.empty or not watchlist_tickers:
        return 0, pd.DataFrame()

    cutoff = date.today() - timedelta(days=alert_window_days)
    normalized = {ticker.upper().strip() for ticker in watchlist_tickers if ticker and ticker.strip()}
    if not normalized:
        return 0, pd.DataFrame()

    alert_rows = filtered[(filtered["reported_on"] >= cutoff) & (filtered["ticker"].str.upper().isin(normalized))]
    if alert_rows.empty:
        return 0, alert_rows
    return len(alert_rows), alert_rows[["reported_on", "actor", "ticker", "action", "source_url"]]


def render_copy_trading_view() -> None:
    """Render public fund/investor/politician disclosure activity."""
    st.subheader("CopyTrading - Public Disclosure Feed")
    st.caption(
        "Tracks publicly disclosed activity only (for example SEC and congressional filings). "
        "Disclosures can be delayed or incomplete; this is for research, not financial advice."
    )

    activities = get_copy_trading_activity()
    actor_type_options = sorted(activities["actor_type"].unique().tolist())

    actor_col, lookback_col, query_col = st.columns([4, 3, 5])
    with actor_col:
        selected_actor_types = st.multiselect(
            "Participant types",
            actor_type_options,
            default=actor_type_options,
            key="copy_trading_actor_types",
        )
    with lookback_col:
        lookback_days = st.slider(
            "Lookback (days)",
            min_value=7,
            max_value=365,
            value=120,
            key="copy_trading_lookback_days",
        )
    with query_col:
        query = st.text_input(
            "Search",
            value="",
            placeholder="Actor, ticker, action, source...",
            key="copy_trading_query",
        )

    filtered = filter_copy_trading_activity(activities, selected_actor_types, lookback_days, query)

    top_metric_cols = st.columns(4)
    with top_metric_cols[0]:
        st.metric("Activities", len(filtered))
    with top_metric_cols[1]:
        st.metric("Actors", int(filtered["actor"].nunique()) if not filtered.empty else 0)
    with top_metric_cols[2]:
        st.metric("Tickers", int(filtered["ticker"].nunique()) if not filtered.empty else 0)
    with top_metric_cols[3]:
        top_type = str(filtered["actor_type"].mode().iloc[0]) if not filtered.empty else "n/a"
        st.metric("Most active type", top_type)

    if filtered.empty:
        st.info("No activities matched the selected filters.")
        return

    available_tickers = sorted({ticker for ticker in filtered["ticker"].astype(str) if ticker.strip()})
    watch_cols = st.columns([6, 4, 4])
    with watch_cols[0]:
        watchlist_from_feed = st.multiselect(
            "Watchlist tickers",
            available_tickers,
            default=[] if "copy_trading_watchlist_tickers" not in st.session_state else st.session_state["copy_trading_watchlist_tickers"],
            key="copy_trading_watchlist_tickers",
            help="Alert when tracked actors report activity in these tickers.",
        )
    with watch_cols[1]:
        manual_watchlist = st.text_input(
            "Additional tickers",
            value="",
            key="copy_trading_watchlist_manual",
            placeholder="TSLA, META",
        )
    with watch_cols[2]:
        alert_window_days = st.slider(
            "Alert window (days)",
            min_value=7,
            max_value=180,
            value=30,
            key="copy_trading_alert_window_days",
        )

    manual_tickers = [ticker.strip().upper() for ticker in manual_watchlist.split(",") if ticker.strip()]
    watchlist_tickers = list(dict.fromkeys([*watchlist_from_feed, *manual_tickers]))
    alert_count, alert_rows = _watchlist_alerts(filtered, watchlist_tickers, alert_window_days)
    if alert_count > 0:
        st.warning(f"{alert_count} watchlist activities detected in the last {alert_window_days} days.")
        st.dataframe(
            alert_rows,
            hide_index=True,
            use_container_width=True,
            column_config={
                "reported_on": st.column_config.DateColumn("Reported on", format="YYYY-MM-DD"),
                "source_url": st.column_config.LinkColumn("Source link", display_text="Open filing"),
            },
        )
    elif watchlist_tickers:
        st.caption(f"No watchlist activity found in the last {alert_window_days} days.")

    st.dataframe(
        filtered,
        hide_index=True,
        use_container_width=True,
        column_config={
            "reported_on": st.column_config.DateColumn("Reported on", format="YYYY-MM-DD"),
            "actor": "Actor",
            "actor_type": "Participant type",
            "ticker": "Ticker",
            "action": "Action",
            "source": "Source",
            "source_url": st.column_config.LinkColumn("Source link", display_text="Open filing"),
            "notes": "Notes",
        },
    )
