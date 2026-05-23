import streamlit as st
import yfinance as yf


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _compute_annualized_volatility(stock):
    try:
        hist = stock.history(period="1y")
        if hist.empty or "Close" not in hist:
            return None
        returns = hist["Close"].pct_change().dropna()
        if returns.empty:
            return None
        return float(returns.std() * (252 ** 0.5) * 100)
    except Exception:
        return None


def _industry_profile(industry):
    low_margin_industries = [
        "utilities",
        "airlines",
        "retail",
        "insurance",
        "banks",
        "energy",
        "automotive",
        "telecom",
    ]
    high_growth_industries = [
        "software",
        "internet",
        "semiconductor",
        "biotechnology",
        "biotech",
        "technology",
    ]

    name = (industry or "Unknown").lower()
    if any(tag in name for tag in high_growth_industries):
        return "high_growth"
    if any(tag in name for tag in low_margin_industries):
        return "low_margin"
    return "balanced"


def _risk_profile(beta, volatility):
    beta_f = _safe_float(beta)
    vol_f = _safe_float(volatility)
    if (beta_f is not None and beta_f >= 1.3) or (vol_f is not None and vol_f >= 35):
        return "high"
    if (beta_f is not None and beta_f <= 0.8) and (vol_f is not None and vol_f <= 20):
        return "low"
    return "moderate"


def _format_range(metric_name, metric_value, context):
    value = _safe_float(metric_value)
    profile = context["industry_profile"]
    risk = context["risk_profile"]

    def classify_higher_better(v, good, bad):
        if v is None:
            return "Current: N/A"
        if v >= good:
            return f"Current {v:.2f}: good"
        if v < bad:
            return f"Current {v:.2f}: weak"
        return f"Current {v:.2f}: mixed"

    def classify_band(v, low_good, high_good, high_bad):
        if v is None:
            return "Current: N/A"
        if low_good <= v <= high_good:
            return f"Current {v:.2f}: good"
        if v > high_bad or v < max(0.0, low_good * 0.5):
            return f"Current {v:.2f}: stretched/risky"
        return f"Current {v:.2f}: mixed"

    if metric_name == "Gross Margin":
        good = 20 if profile == "low_margin" else 35
        bad = 8 if profile == "low_margin" else 15
        return f"Good >= {good}%, weak < {bad}%. {classify_higher_better(value, good, bad)}"
    if metric_name == "Operating Margin":
        good = 12 if profile == "low_margin" else 18
        bad = 3 if profile == "low_margin" else 6
        return f"Good >= {good}%, weak < {bad}%. {classify_higher_better(value, good, bad)}"
    if metric_name == "ROCE":
        good = 18 if risk == "high" else 15
        bad = 8
        return f"Good >= {good}%, weak < {bad}%. {classify_higher_better(value, good, bad)}"
    if metric_name in ("P/E", "Forward P/E"):
        high_good = 28 if profile == "high_growth" else 22
        high_bad = 40 if profile == "high_growth" else 32
        return f"Good range 8-{high_good}, stretched > {high_bad}. {classify_band(value, 8, high_good, high_bad)}"
    if metric_name == "P/B":
        high_good = 6 if profile == "high_growth" else 4
        high_bad = 9 if profile == "high_growth" else 7
        return f"Good range 1-{high_good}, stretched > {high_bad}. {classify_band(value, 1, high_good, high_bad)}"
    if metric_name == "Sales YoY":
        good = 15 if profile == "high_growth" else 8
        bad = 0
        return f"Good >= {good}%, weak < {bad}%. {classify_higher_better(value, good, bad)}"
    if metric_name == "EPS YoY":
        good = 18 if profile == "high_growth" else 10
        bad = 0
        return f"Good >= {good}%, weak < {bad}%. {classify_higher_better(value, good, bad)}"
    if metric_name == "P/S":
        high_good = 10 if profile == "high_growth" else 4
        high_bad = 18 if profile == "high_growth" else 8
        return f"Good range 1-{high_good}, stretched > {high_bad}. {classify_band(value, 1, high_good, high_bad)}"
    if metric_name == "PEG":
        return f"Good range 0.8-1.8, weak > 2.5 or <= 0. {classify_band(value, 0.8, 1.8, 2.5)}"
    if metric_name == "FCF Margin":
        good = 8 if profile == "low_margin" else 12
        bad = 2
        return f"Good >= {good}%, weak < {bad}%. {classify_higher_better(value, good, bad)}"
    if metric_name == "FCF Yield":
        good = 5 if risk == "high" else 4
        bad = 1.5
        return f"Good >= {good}%, weak < {bad}%. {classify_higher_better(value, good, bad)}"
    if metric_name == "EV/EBITDA":
        high_good = 16 if profile == "high_growth" else 12
        high_bad = 24 if profile == "high_growth" else 18
        return f"Good range 6-{high_good}, stretched > {high_bad}. {classify_band(value, 6, high_good, high_bad)}"
    return "Metric guidance unavailable."


def _metric_help_text(metric_name, metric_value, context):
    beta_txt = f"{context['beta']:.2f}" if context["beta"] is not None else "N/A"
    vol_txt = f"{context['volatility']:.1f}%" if context["volatility"] is not None else "N/A"
    context_line = (
        f"Context: {context['ticker']} in {context['industry']}; "
        f"risk {context['risk_profile']} (beta {beta_txt}), volatility {vol_txt}."
    )
    range_line = _format_range(metric_name, metric_value, context)
    return f"{context_line}\n\n{range_line}"

st.title("Stock Quality Dashboard")

ticker = st.text_input("Enter Ticker", "AAPL")
if st.button("Analyze"):
    stock = yf.Ticker(ticker)
    info = stock.info
    fin = stock.financials
    qfin = stock.quarterly_financials
    cf = stock.cashflow
    bs = stock.balance_sheet

    # Quality
    rev = fin.loc['Total Revenue'].iloc[0] if 'Total Revenue' in fin.index else 0
    gp = fin.loc['Gross Profit'].iloc[0] if 'Gross Profit' in fin.index else 0
    gm = (gp / rev * 100) if rev else None
    op = fin.loc['Operating Income'].iloc[0] if 'Operating Income' in fin.index else 0
    om = (op / rev * 100) if rev else None
    ta = bs.loc['Total Assets'].iloc[0] if 'Total Assets' in bs.index else 0
    cl = bs.loc['Current Liabilities'].iloc[0] if 'Current Liabilities' in bs.index else 0
    ebit = fin.loc['EBIT'].iloc[0] if 'EBIT' in fin.index else op
    roce = (ebit / (ta - cl) * 100) if (ta - cl) else None

    sales_yoy = info.get('revenueGrowth', None)
    eps_yoy = info.get('earningsGrowth', None)
    pe_ratio = info.get('trailingPE', None)
    fwd_pe = info.get('forwardPE', None)
    pb_ratio = info.get('priceToBook', None)
    ps_ratio = info.get('priceToSalesTrailing12Months', None)
    peg_ratio = info.get('pegRatio', None)
    ev_ebitda = info.get('enterpriseToEbitda', None)
    market_cap = info.get('marketCap', None)
    beta = _safe_float(info.get('beta', None))
    industry_name = info.get('industry', 'Unknown')
    annualized_volatility = _compute_annualized_volatility(stock)
    metric_context = {
        "ticker": ticker,
        "industry": industry_name,
        "beta": beta,
        "volatility": annualized_volatility,
        "risk_profile": _risk_profile(beta, annualized_volatility),
        "industry_profile": _industry_profile(industry_name),
    }
    fcf = cf.loc['Free Cash Flow'].iloc[0] if 'Free Cash Flow' in cf.index else None
    fcf_margin = (fcf / rev * 100) if fcf and rev else None
    fcf_yield = (fcf / market_cap * 100) if (fcf is not None and market_cap) else None

    quality_col, growth_col, cashflow_col = st.columns(3)

    with quality_col:
        st.subheader("Quality")
        st.metric(
            "Gross Margin",
            f"{gm:.1f}%" if gm is not None else "N/A",
            help=_metric_help_text("Gross Margin", gm, metric_context),
        )
        st.metric(
            "Operating Margin",
            f"{om:.1f}%" if om is not None else "N/A",
            help=_metric_help_text("Operating Margin", om, metric_context),
        )
        st.metric(
            "ROCE",
            f"{roce:.1f}%" if roce is not None else "N/A",
            help=_metric_help_text("ROCE", roce, metric_context),
        )

        quality_extra_cards = [
            ("P/E", pe_ratio, "{:.2f}"),
            ("Forward P/E", fwd_pe, "{:.2f}"),
            ("P/B", pb_ratio, "{:.2f}"),
        ]
        for label, metric_value, fmt in quality_extra_cards:
            if metric_value is not None:
                st.metric(label, fmt.format(metric_value), help=_metric_help_text(label, metric_value, metric_context))

    with growth_col:
        st.subheader("Growth")
        st.metric(
            "Sales YoY",
            f"+{sales_yoy*100:.1f}%" if sales_yoy is not None else "N/A",
            help=_metric_help_text("Sales YoY", sales_yoy * 100 if sales_yoy is not None else None, metric_context),
        )
        st.metric(
            "EPS YoY",
            f"+{eps_yoy*100:.1f}%" if eps_yoy is not None else "N/A",
            help=_metric_help_text("EPS YoY", eps_yoy * 100 if eps_yoy is not None else None, metric_context),
        )

        growth_extra_cards = [
            ("P/S", ps_ratio, "{:.2f}"),
            ("PEG", peg_ratio, "{:.2f}"),
        ]
        for label, metric_value, fmt in growth_extra_cards:
            if metric_value is None:
                continue
            st.metric(label, fmt.format(metric_value), help=_metric_help_text(label, metric_value, metric_context))

    with cashflow_col:
        st.subheader("Cash Flow")
        st.metric(
            "FCF Margin",
            f"{fcf_margin:.1f}%" if fcf_margin is not None else "N/A",
            help=_metric_help_text("FCF Margin", fcf_margin, metric_context),
        )

        cashflow_extra_cards = [
            ("FCF Yield", fcf_yield, "{:.2f}%"),
            ("EV/EBITDA", ev_ebitda, "{:.2f}"),
        ]
        for label, metric_value, fmt in cashflow_extra_cards:
            if metric_value is None:
                continue
            st.metric(label, fmt.format(metric_value), help=_metric_help_text(label, metric_value, metric_context))