import streamlit as st
import pandas as pd
import yfinance as yf
from .charts import get_trend_colors, render_chart, render_stock_chart
from .constants import INDUSTRY_GRID_COLS, SECTOR_FIGSIZE, SECTOR_GRID_COLS
from .data import (
    compute_industry_aggregate,
    fetch_industry_counts,
    fetch_industry_tickers,
    fetch_sector_data,
    fetch_ticker_data_batch,
    get_db_sector_name,
    load_equities,
)
from .universe import get_universe_tickers, get_universe_industries, get_sector_industry_counts, get_universe_sector_stock_count, get_universe_stock_name


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
    selected_universe = st.session_state.get("selected_universe", "S&P 500")
    counts = get_sector_industry_counts(selected_universe, sector)
    industries = [ind for ind in counts if ind != 'undefined']
    undef_count = counts.get('undefined', 0)
    total = sum(counts.values())

    if not counts:
        st.write("No industries found.")
        return

    # Header summary
    st.caption(
        f"**{total} stocks** total — {len(industries)} industries"
        + (f" · **{undef_count} unclassified**" if undef_count else "")
    )

    columns = st.columns(INDUSTRY_GRID_COLS)
    for i, industry in enumerate(industries):
        with columns[i % INDUSTRY_GRID_COLS]:
            tickers = get_universe_tickers(selected_universe, sector=sector, industry=industry)
            count = len(tickers)

            if tickers:
                with st.spinner(f"Building {industry} aggregate..."):
                    avg_close, total_volume, num_fetched = compute_industry_aggregate(tickers)
                render_data_card(
                    title=f"{industry} ({count})",
                    close=avg_close,
                    volume=total_volume,
                    chart_params={"y_label": "Index", "legend_label": "Index", "figsize": (4, 2.5)},
                    nav_action=lambda ind=industry: _nav_to_industry_stocks(sector, ind),
                )
            else:
                st.subheader(f"{industry} ({count})")
                st.caption("No data")

    # Unclassified group — shown after all named industries
    if undef_count:
        undef_tickers = get_universe_tickers(selected_universe, sector=sector, industry='undefined')
        col_idx = len(industries) % INDUSTRY_GRID_COLS
        with columns[col_idx]:
            st.subheader(f"Unclassified ({undef_count})")
            st.caption("No industry assigned")
            _nav_to_industry_stocks(sector, 'undefined')


def _nav_to_industry_stocks(sector: str, industry: str) -> None:
    if st.button(f"View Stocks", key=f"stocks-{sector}-{industry}"):
        st.session_state.view = "industry_stocks"
        st.session_state.selected_sector = sector
        st.session_state.selected_industry = industry
        st.rerun()


def _compute_stock_metrics(df: pd.DataFrame, ticker: str) -> dict:
    """Compute key metrics for a stock including technicals and fundamentals."""
    metrics = {}
    
    # Technical metrics
    if not df.empty and "Close" in df.columns:
        close = df["Close"]
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
    
    # Fundamental metrics via yfinance
    try:
        tick = yf.Ticker(ticker)
        info = tick.info or {}
        
        metrics.update({
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "dividend_yield": info.get("dividendYield"),
            "pb_ratio": info.get("priceToBook"),
            "debt_to_equity": info.get("debtToEquity"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "eps_trailing": info.get("trailingEps"),
            "eps_forward": info.get("forwardEps"),
            "dividend_per_share": info.get("dividendRate"),
        })
        
        # Recent earnings dates
        try:
            earnings_dates = tick.quarterly_financials
            if not earnings_dates.empty:
                latest_earnings_date = earnings_dates.columns[0]
                metrics["latest_earnings_date"] = latest_earnings_date
        except:
            pass
            
    except Exception:
        pass
    
    return metrics


def _format_fundamental(val, is_pct=False):
    """Format fundamental metric values."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    try:
        val = float(val)
        if is_pct:
            return f"{val*100:.1f}%"
        elif val >= 1e9:
            return f"${val/1e9:.1f}B"
        elif val >= 1e6:
            return f"${val/1e6:.1f}M"
        else:
            return f"{val:.2f}"
    except (ValueError, TypeError):
        return "N/A"


def _render_stock_details_panel(metrics: dict, company_name: str, ticker: str) -> None:
    """Render a compact 3-column details panel sized to sit beside the chart."""
    price = f"${metrics.get('latest', 0):.2f}"
    change = f"{metrics.get('change_20d_pct', 0):+.1f}%"
    detail_items = [
        ("Price", price, change),
        ("Vol (20D)", f"{metrics.get('volatility_20d', 0):.1f}%", ""),
        ("Market Cap", _format_fundamental(metrics.get('market_cap')), ""),
        ("P/E", _format_fundamental(metrics.get('pe_ratio')), ""),
        ("P/B", _format_fundamental(metrics.get('pb_ratio')), ""),
        ("EPS (TTM)", _format_fundamental(metrics.get('eps_trailing')), ""),
        ("ROE", _format_fundamental(metrics.get('roe'), is_pct=True), ""),
        ("Div Yield", _format_fundamental(metrics.get('dividend_yield'), is_pct=True), ""),
        ("Debt/Eq", _format_fundamental(metrics.get('debt_to_equity')), ""),
    ]

    st.markdown(
        """
        <style>
        .stock-details-panel {
            display: block;
        }
        .stock-details-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.22rem;
            grid-auto-rows: auto;
        }
        .stock-details-name {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 0.5rem;
            padding: 0.35rem 0.45rem;
            margin-bottom: 0.3rem;
            background: rgba(255, 255, 255, 0.02);
        }
        .stock-details-name-label {
            font-size: 0.65rem;
            line-height: 1.1;
            opacity: 0.72;
            margin-bottom: 0.18rem;
        }
        .stock-details-name-value {
            font-size: 0.82rem;
            line-height: 1.2;
            font-weight: 600;
            word-break: break-word;
        }
        .stock-details-card {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 0.5rem;
            padding: 0.2rem 0.28rem;
            min-height: 2.55rem;
            background: rgba(255, 255, 255, 0.02);
        }
        .stock-details-label {
            font-size: 0.56rem;
            line-height: 1.02;
            opacity: 0.72;
            margin-bottom: 0.07rem;
        }
        .stock-details-value {
            font-size: 0.76rem;
            line-height: 1.04;
            font-weight: 600;
            word-break: break-word;
        }
        .stock-details-delta {
            font-size: 0.56rem;
            line-height: 1.0;
            opacity: 0.8;
            margin-top: 0.05rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    cards = []
    for label, value, delta in detail_items:
        delta_html = f'<div class="stock-details-delta">{delta}</div>' if delta else ""
        cards.append(
            f'<div class="stock-details-card">'
            f'<div class="stock-details-label">{label}</div>'
            f'<div class="stock-details-value">{value}</div>'
            f'{delta_html}'
            f'</div>'
        )

    st.markdown(
        (
            '<div class="stock-details-panel">'
            '<div class="stock-details-name">'
            '<div class="stock-details-name-label">Company</div>'
            f'<div class="stock-details-name-value">{company_name} ({ticker})</div>'
            '</div>'
            f'<div class="stock-details-grid">{"".join(cards)}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def render_industry_stock_page(sector: str, industry: str) -> None:
    selected_universe = st.session_state.get("selected_universe", "S&P 500")
    all_tickers = get_universe_tickers(selected_universe, sector=sector, industry=industry)
    st.caption(f"{len(all_tickers)} stocks in {selected_universe}")
    
    # Display stocks in 2-column layout for larger charts
    for row_start in range(0, len(all_tickers), 2):
        row_tickers = all_tickers[row_start:row_start + 2]
        cols = st.columns(2)
        for col_idx, ticker in enumerate(row_tickers):
            with cols[col_idx]:
                with st.spinner(f"Loading {ticker}..."):
                    _, df = fetch_ticker_data_batch(ticker, False)
                    metrics = _compute_stock_metrics(df, ticker) if not df.empty else {}
                    company_name = get_universe_stock_name(selected_universe, ticker)
                if df.empty or "Close" not in df.columns or "Volume" not in df.columns:
                    st.write(f"{ticker} could not be loaded")
                    continue

                # Keep graph and details equally wide for balanced screen usage.
                chart_col, details_col = st.columns([1, 1])
                with chart_col:
                    render_stock_chart(df, ticker)

                with details_col:
                    if metrics:
                        _render_stock_details_panel(metrics, company_name, ticker)
                    else:
                        st.caption("No snapshot metrics available.")

    st.success(f"✓ Complete! Displayed all {len(all_tickers)} stocks")


def _render_sector_industry_summary(universe: str, sector: str) -> None:
    """Render a compact stock-count summary broken down by industry."""
    counts = get_sector_industry_counts(universe, sector)
    total = sum(counts.values())
    undef_count = counts.get('undefined', 0)
    assigned = total - undef_count

    st.caption(f"**{total} stocks** · {assigned} classified · {undef_count} unclassified")

    if counts:
        rows = []
        for industry, cnt in counts.items():
            label = "_(unclassified)_" if industry == 'undefined' else industry
            rows.append(f"- {label}: **{cnt}**")
        st.markdown("\n".join(rows))


def render_sector_card(name: str, ticker: str) -> None:
    with st.spinner(f"Loading {name}..."):
        df = fetch_sector_data(ticker)
    close = df["Close"].squeeze() if not df.empty else pd.Series()
    volume = df["Volume"].squeeze() if not df.empty else pd.Series()

    selected_universe = st.session_state.get("selected_universe", "S&P 500")
    summary_sector = name
    if not get_sector_industry_counts(selected_universe, name):
        from .constants import SECTOR_NAME_MAP
        long_name = SECTOR_NAME_MAP.get(name)
        if long_name:
            summary_sector = long_name

    def nav_to_industry() -> None:
        if st.button(f"View Industries", key=name):
            st.session_state.view = "industry"
            st.session_state.selected_sector = name
            st.session_state.pop("selected_industry", None)
            st.rerun()

    st.subheader(f"{name} ({ticker})")
    chart_col, details_col = st.columns([1, 1])

    with chart_col:
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
        nav_to_industry()

    with details_col:
        _render_sector_industry_summary(selected_universe, summary_sector)
