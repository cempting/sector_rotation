import html
from collections.abc import Callable
from typing import Any

import pandas as pd
import streamlit as st

from .stock_focus import open_dedicated_stock_view
from .view_config import FAVORITES_PANEL_MIN_HEIGHT_REM


def format_fundamental(val: object, is_pct: bool = False) -> str:
    """Format fundamental metric values for stock details cards."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    try:
        num = float(val)
        if is_pct:
            return f"{num * 100:.1f}%"
        if num >= 1e9:
            return f"${num / 1e9:.1f}B"
        if num >= 1e6:
            return f"${num / 1e6:.1f}M"
        return f"{num:.2f}"
    except (ValueError, TypeError):
        return "N/A"


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        num = float(value)
    except (ValueError, TypeError):
        return None
    if pd.isna(num):
        return None
    return num


def _industry_profile(industry: str) -> str:
    low_margin_industries = (
        "utilities",
        "airlines",
        "retail",
        "insurance",
        "banks",
        "energy",
        "automotive",
        "telecom",
    )
    high_growth_industries = (
        "software",
        "internet",
        "semiconductor",
        "biotech",
        "technology",
    )
    financial_industries = (
        "bank",
        "insurance",
        "asset management",
        "capital markets",
        "financial",
    )

    name = (industry or "").lower()
    if any(tag in name for tag in financial_industries):
        return "financial"
    if any(tag in name for tag in high_growth_industries):
        return "high_growth"
    if any(tag in name for tag in low_margin_industries):
        return "low_margin"
    return "balanced"


def _risk_profile(beta: float | None, vol_20d: float | None) -> str:
    if (beta is not None and beta >= 1.3) or (vol_20d is not None and vol_20d >= 3.5):
        return "high"
    if (beta is not None and beta <= 0.8) and (vol_20d is not None and vol_20d <= 2.0):
        return "low"
    return "moderate"


def _evaluate_metric_range(metric_name: str, metric_value: object, context: dict[str, object]) -> str:
    value = _safe_float(metric_value)
    profile = str(context.get("industry_profile", "balanced"))
    risk = str(context.get("risk_profile", "moderate"))

    def higher_better(v: float | None, good: float, bad: float) -> str:
        if v is None:
            return "Current: N/A"
        if v >= good:
            return f"Current {v:.2f}: good"
        if v < bad:
            return f"Current {v:.2f}: weak"
        return f"Current {v:.2f}: mixed"

    def good_band(v: float | None, lo: float, hi: float, stretched: float) -> str:
        if v is None:
            return "Current: N/A"
        if lo <= v <= hi:
            return f"Current {v:.2f}: good"
        if v > stretched or v < max(0.0, lo * 0.5):
            return f"Current {v:.2f}: stretched/risky"
        return f"Current {v:.2f}: mixed"

    if metric_name == "Gross Margin":
        if profile == "financial":
            if value is None:
                return "Gross margin is typically not comparable for financials. Use ROE/ROA and credit metrics instead. Current: N/A"
            return f"Gross margin is typically not comparable for financials. Use ROE/ROA and credit metrics instead. Current {value:.2f}: mixed"
        good = 20 if profile == "low_margin" else 35
        bad = 8 if profile == "low_margin" else 15
        return f"Good >= {good}%, weak < {bad}%. {higher_better(value, good, bad)}"
    if metric_name == "Operating Margin":
        good = 12 if profile == "low_margin" else 18
        bad = 3 if profile == "low_margin" else 6
        return f"Good >= {good}%, weak < {bad}%. {higher_better(value, good, bad)}"
    if metric_name == "ROCE":
        good = 18 if risk == "high" else 15
        return f"Good >= {good}%, weak < 8%. {higher_better(value, good, 8)}"
    if metric_name in ("P/E", "Forward P/E"):
        hi = 28 if profile == "high_growth" else 22
        stretched = 40 if profile == "high_growth" else 32
        return f"Good range 8-{hi}, stretched > {stretched}. {good_band(value, 8, hi, stretched)}"
    if metric_name == "P/B":
        hi = 6 if profile == "high_growth" else 4
        stretched = 9 if profile == "high_growth" else 7
        return f"Good range 1-{hi}, stretched > {stretched}. {good_band(value, 1, hi, stretched)}"
    if metric_name == "Sales YoY":
        good = 15 if profile == "high_growth" else 8
        return f"Good >= {good}%, weak < 0%. {higher_better(value, good, 0)}"
    if metric_name == "EPS YoY":
        good = 18 if profile == "high_growth" else 10
        return f"Good >= {good}%, weak < 0%. {higher_better(value, good, 0)}"
    if metric_name == "P/S":
        hi = 10 if profile == "high_growth" else 4
        stretched = 18 if profile == "high_growth" else 8
        return f"Good range 1-{hi}, stretched > {stretched}. {good_band(value, 1, hi, stretched)}"
    if metric_name == "PEG":
        return f"Good range 0.8-1.8, weak > 2.5 or <= 0. {good_band(value, 0.8, 1.8, 2.5)}"
    if metric_name == "FCF Margin":
        good = 8 if profile == "low_margin" else 12
        return f"Good >= {good}%, weak < 2%. {higher_better(value, good, 2)}"
    if metric_name == "FCF Yield":
        good = 5 if risk == "high" else 4
        return f"Good >= {good}%, weak < 1.5%. {higher_better(value, good, 1.5)}"
    if metric_name == "EV/EBITDA":
        hi = 16 if profile == "high_growth" else 12
        stretched = 24 if profile == "high_growth" else 18
        return f"Good range 6-{hi}, stretched > {stretched}. {good_band(value, 6, hi, stretched)}"
    return "Metric guidance unavailable."


def _metric_help_text(metric_name: str, metric_value: object, context: dict[str, object]) -> str:
    beta = _safe_float(context.get("beta"))
    beta_txt = f"{beta:.2f}" if beta is not None else "N/A"
    vol_20d = _safe_float(context.get("volatility_20d"))
    vol_txt = f"{vol_20d:.1f}%" if vol_20d is not None else "N/A"
    context_line = (
        f"Context: {context.get('ticker', 'N/A')} in {context.get('industry', 'N/A')}; "
        f"risk {context.get('risk_profile', 'N/A')} (beta {beta_txt}), 20D volatility {vol_txt}."
    )
    return f"{context_line}\n\n{_evaluate_metric_range(metric_name, metric_value, context)}"


def _metric_status(metric_name: str, metric_value: object, context: dict[str, object]) -> str:
    guidance = _evaluate_metric_range(metric_name, metric_value, context).lower()

    # Evaluate only the current assessment segment to avoid matching threshold text
    # like "Good >= ..." in the guidance prefix.
    current_segment = guidance.split("current", 1)[1] if "current" in guidance else guidance

    if "n/a" in current_segment:
        return "moderate"
    if "good" in current_segment:
        return "good"
    if "mixed" in current_segment:
        return "moderate"
    return "weak"


def _status_color(status: str) -> str:
    if status == "good":
        return "#4ecb71"
    if status == "moderate":
        return "#f2c94c"
    return "#ff6b6b"


def _score_from_status(status: str) -> int:
    if status == "good":
        return 100
    if status == "moderate":
        return 60
    return 25


def _field_explanation(label: str) -> str:
    explanations = {
        "Gross Margin": "Gross margin is gross profit divided by revenue. It shows how much of each sales dollar remains after direct production costs.",
        "Operating Margin": "Operating margin is operating income divided by revenue. It measures profitability after operating costs, before interest and taxes.",
        "ROCE": "Return on Capital Employed (ROCE) is EBIT divided by capital employed. It indicates how efficiently the business generates operating profit from invested capital.",
        "P/E": "Price-to-Earnings (P/E) compares share price to trailing earnings per share. Higher values imply investors pay more for each unit of current earnings.",
        "Forward P/E": "Forward P/E compares share price to expected next-year earnings per share. It reflects valuation based on forecast earnings.",
        "P/B": "Price-to-Book (P/B) compares market value to book equity. It indicates how far the market prices the company above or below accounting net assets.",
        "Sales YoY": "Year-over-year sales growth compares revenue to the same period a year ago. It is a core measure of top-line expansion.",
        "EPS YoY": "Year-over-year EPS growth compares earnings per share to the same period last year. It reflects profit growth attributable to each share.",
        "P/S": "Price-to-Sales (P/S) compares market value to revenue. It is often used for companies where earnings are volatile or currently low.",
        "PEG": "PEG is P/E divided by earnings growth rate. Around 1 can indicate valuation is aligned with growth, while much higher can indicate expensive growth pricing.",
        "FCF Margin": "Free-cash-flow margin is free cash flow divided by revenue. It shows how effectively revenue is converted into cash after operating and capital spending needs.",
        "FCF Yield": "Free-cash-flow yield is free cash flow divided by market capitalization. It estimates cash return generated relative to the market value of the company.",
        "EV/EBITDA": "EV/EBITDA compares enterprise value to EBITDA. It is a capital-structure-neutral valuation multiple often used for cross-company comparisons.",
        "Price": "Latest traded stock price from recent market data.",
        "20D Change": "Percent price change over the last 20 trading days.",
        "Volatility": "Historical 20-day price volatility; higher values mean larger daily swings.",
        "Regime": "Simple market state inferred from recent momentum (Risk-On vs Risk-Off).",
        "Composite": "Combined score blending Quality, Growth, Cash Flow, and Risk lenses.",
        "Quality": "Profitability and efficiency lens based on margins, returns, and valuation context.",
        "Growth": "Business growth lens using revenue/earnings momentum and valuation support.",
        "Cash Flow": "Cash generation lens combining free-cash-flow strength and valuation support.",
        "Risk": "Risk lens based on volatility, beta, and risk/reward balance.",
        "Risk/Reward": "Expected return divided by expected volatility over the selected lookback.",
        "Beta": "Sensitivity versus the broad market. 1.0 is market-like risk.",
        "Volatility 20D": "Recent 20-day annualized volatility estimate.",
        "Fundamental %ile": "Aggregate percentile-like score from Quality, Growth, and Cash Flow lenses.",
        "Risk-Adjusted %ile": "Blend of Risk and Quality to reflect durability of returns.",
        "Liquidity Shift": "How recent trading flow compares with prior periods.",
        "Flow Trend (3M)": "Dollar-volume trend over roughly the last 3 months.",
        "Flow Trend (6M)": "Dollar-volume trend over roughly the last 6 months.",
        "Weekly Acceleration": "Short-term acceleration/deceleration in weekly trading flow.",
        "Flow Ratio": "Recent 20-day dollar volume relative to a 60-day baseline.",
        "Macro Impact": "How macro factors currently relate to this stock's behavior.",
        "Impact": "Overall macro interpretation of the stock's recent correlation profile.",
        "Driver": "Macro factor with strongest recent relationship to returns.",
        "Beta Profile": "Interpretation of whether behavior is pro-cyclical or defensive.",
        "Market Regime (3M)": "Broad market/rates regime estimate over approximately 3 months.",
        "Ratings & Relative Strength": "Analyst snapshot plus relative momentum versus industry peers.",
        "Analyst Rating": "Latest consensus analyst recommendation summary.",
        "Rating Detail": "Additional context behind the current analyst snapshot.",
        "MRSI vs Industry": "Momentum/relative-strength signal versus industry average.",
        "Recent Headlines": "Most recent available news headlines for this ticker.",
        "News Feed": "Recent headline stream used for quick qualitative context.",
    }
    return explanations.get(label, f"Definition for '{label}' in this stock details context.")


def _tooltip_attr(label: str, fallback: str | None = None) -> str:
    tip = fallback or _field_explanation(label)
    return html.escape(tip).replace("\n", "&#10;")


def _render_colored_detail_card(label: str, value: str, status: str, help_text: str, eval_text: str) -> None:
    safe_help = _tooltip_attr(label, f"{_field_explanation(label)}\n\n{help_text}")
    safe_label = html.escape(label)
    safe_value = html.escape(value)
    safe_eval = html.escape(eval_text)
    st.markdown(
        (
            f'<div class="sr-details-card" title="{safe_help}">'
            f'<div class="sr-details-label">{safe_label}</div>'
            f'<div class="sr-details-value sr-{status}">{safe_value}</div>'
            f'<div class="sr-details-explain">{safe_eval}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_score_bar(label: str, score: float) -> None:
    clamped = max(0.0, min(100.0, float(score)))
    if clamped >= 75:
        status = "good"
    elif clamped >= 45:
        status = "moderate"
    else:
        status = "weak"
    color = _status_color(status)
    st.markdown(
        (
            f'<div class="sr-score-row" title="{_tooltip_attr(label)}">'
            '<div class="sr-score-head">'
            f'<div class="sr-score-label">{html.escape(label)}</div>'
            f'<div class="sr-score-value">{clamped:.0f}</div>'
            "</div>"
            '<div class="sr-score-track">'
            f'<div class="sr-score-fill" style="width:{clamped:.0f}%; background:{color};"></div>'
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_stock_header(
    company_name: str,
    ticker: str,
    sector: str,
    industry: str,
    favorite_label: str,
    favorite_button_key: str,
    on_toggle: Callable[..., Any],
    on_toggle_args: tuple[Any, ...],
    show_full_details: bool,
) -> None:
    if show_full_details:
        header_col, action_col = st.columns([5, 2])
        with header_col:
            st.markdown(
                (
                    '<div class="stock-details-name">'
                    '<div class="stock-details-name-label">Company</div>'
                    f'<div class="stock-details-name-value">{company_name} ({ticker})</div>'
                    f'<div class="stock-details-delta">Sector: {html.escape(sector)} · Industry: {html.escape(industry)}</div>'
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
        with action_col:
            st.button(
                favorite_label,
                key=favorite_button_key,
                on_click=on_toggle,
                args=on_toggle_args,
                help="Toggle favorite",
                use_container_width=True,
            )
        return

    header_col, name_col = st.columns([0.7, 6.3])
    with header_col:
        st.button(
            favorite_label,
            key=favorite_button_key,
            on_click=on_toggle,
            args=on_toggle_args,
            help="Toggle favorite",
            use_container_width=True,
        )
    with name_col:
        st.markdown(
            (
                '<div class="stock-details-name">'
                f'<div class="stock-details-name-value">{company_name} ({ticker})</div>'
                f'<div class="stock-details-delta">{html.escape(sector)} · {html.escape(industry)}</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def _section_score(entries: list[tuple[str, object, str]], context: dict[str, object]) -> float:
    statuses = [_metric_status(label, raw, context) for label, raw, _ in entries]
    if not statuses:
        return 0.0
    return sum(_score_from_status(status) for status in statuses) / len(statuses)


def _render_metric_cards(entries: list[tuple[str, object, str]], context: dict[str, object]) -> None:
    for label, raw, value in entries:
        _render_colored_detail_card(
            label,
            value,
            _metric_status(label, raw, context),
            _metric_help_text(label, raw, context),
            _evaluate_metric_range(label, raw, context),
        )


def _render_score_bars(entries: list[tuple[str, float]]) -> None:
    for label, score in entries:
        _render_score_bar(label, score)


def _pane_start(title: str) -> None:
    st.markdown(f'<div class="sr-pane"><div class="sr-pane-title">{html.escape(title)}</div>', unsafe_allow_html=True)


def _pane_end() -> None:
    st.markdown('</div>', unsafe_allow_html=True)


def _lens_frame(rows: list[tuple[str, float]], fallback_label: str) -> pd.DataFrame:
    lens_rows = rows if rows else [(fallback_label, 0.0)]
    return pd.DataFrame(lens_rows, columns=["lens", "value"]).set_index("lens")


def _render_criteria_row(
    category_label: str,
    score: float,
    metric_entries: list[tuple[str, object, str]],
    context: dict[str, object],
    extra_cards: list[tuple[str, str, str, str, str]] | None = None,
) -> None:
    """Responsive criteria rows: score panel left, cards wrapped across rows."""
    extra = extra_cards or []
    card_items: list[tuple[str, str, str, str, str]] = []
    for label, raw, value in metric_entries:
        card_items.append(
            (
                label,
                value,
                _metric_status(label, raw, context),
                _metric_help_text(label, raw, context),
                _evaluate_metric_range(label, raw, context),
            )
        )
    card_items.extend(extra)

    n_cards = len(card_items)
    if n_cards == 0:
        return

    clamped = max(0.0, min(100.0, float(score)))
    status = "good" if clamped >= 75 else "moderate" if clamped >= 45 else "weak"
    color = _status_color(status)

    # Keep rows compact so cards remain legible on laptop/mobile widths.
    max_cards_per_row = 3
    for row_start in range(0, n_cards, max_cards_per_row):
        row_cards = card_items[row_start: row_start + max_cards_per_row]
        widths = [1.2] + [1.0] * len(row_cards)

        category_slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in category_label).strip("-") or "category"
        row_key = f"sr-row-{status}-{category_slug}-{row_start}"
        with st.container(key=row_key):
            cols = st.columns(widths)

            with cols[0]:
                if row_start == 0:
                    st.markdown(
                        (
                            f'<div class="sr-criteria-score-panel" title="{_tooltip_attr(category_label)}">'
                            f'<div class="sr-criteria-score-label">{html.escape(category_label)}</div>'
                            f'<div class="sr-criteria-score-value" style="color:{color};">{clamped:.0f}</div>'
                            '<div class="sr-score-track">'
                            f'<div class="sr-score-fill" style="width:{clamped:.0f}%; background:{color};"></div>'
                            "</div>"
                            "</div>"
                        ),
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown('<div class="sr-criteria-spacer"></div>', unsafe_allow_html=True)

            for idx, (label, value, card_status, help_text, eval_text) in enumerate(row_cards):
                with cols[idx + 1]:
                    _render_colored_detail_card(label, value, card_status, help_text, eval_text)


def _render_compact_stock_panel(
    universe: str,
    ticker: str,
    composite_score: float,
    quality_score: float,
    growth_score: float,
    cashflow_score: float,
    risk_score: float,
) -> None:
    _render_score_bars(
        [
            ("Composite", composite_score),
            ("Quality", quality_score),
            ("Growth", growth_score),
            ("Cash Flow", cashflow_score),
            ("Risk", risk_score),
        ]
    )
    action_col = st.columns([4, 1])[0]
    with action_col:
        st.markdown('<div class="sr-open-primary">', unsafe_allow_html=True)
        if st.button(
            "Open Dedicated Stock View (Full Analysis)",
            key=f"details-open-{universe}-{ticker}",
            use_container_width=True,
        ):
            open_dedicated_stock_view(universe, ticker)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def _render_trend_lenses_pane(metrics: dict[str, object]) -> None:
    _pane_start("Trend Lenses")

    def _as_history_map(key: str) -> dict[str, float]:
        raw = metrics.get(key)
        if not isinstance(raw, dict):
            return {}
        out: dict[str, float] = {}
        for year, value in raw.items():
            num = _safe_float(value)
            if num is None:
                continue
            out[str(year)] = float(num)
        return out

    quality_hist = _as_history_map("quality_history_quarterly_pct")
    growth_hist = _as_history_map("growth_history_quarterly_pct")
    cashflow_hist = _as_history_map("cashflow_history_quarterly_pct")
    quarterly_mode = bool(quality_hist or growth_hist or cashflow_hist)

    if not quarterly_mode:
        quality_hist = _as_history_map("quality_history_annual_pct")
        growth_hist = _as_history_map("growth_history_annual_pct")
        cashflow_hist = _as_history_map("cashflow_history_annual_pct")

    if not quality_hist and not growth_hist and not cashflow_hist:
        st.caption("No multi-year fundamentals available yet for Quality/Growth/Cash Flow trend lenses.")
        _pane_end()
        return

    period_rows: dict[str, dict[str, float]] = {}

    def _period_sort_key(label: str) -> int:
        text = str(label)
        if "-Q" in text:
            year_text, quarter_text = text.split("-Q", 1)
            try:
                year = int(year_text)
                quarter = int(quarter_text)
                return year * 4 + max(1, min(4, quarter))
            except (TypeError, ValueError):
                return -1
        try:
            year = int(text)
            return year * 4 + 4
        except (TypeError, ValueError):
            return -1

    def _add_series(series_name: str, values: dict[str, float]) -> None:
        for period_label, metric_val in values.items():
            period_rows.setdefault(str(period_label), {})[series_name] = metric_val

    _add_series("Quality", quality_hist)
    _add_series("Growth", growth_hist)
    _add_series("Cash Flow", cashflow_hist)

    if not period_rows:
        st.caption("No valid period history points were found for trend lenses.")
        _pane_end()
        return

    ordered_periods = sorted(period_rows.keys(), key=_period_sort_key)
    trend_df = pd.DataFrame([period_rows[p] for p in ordered_periods], index=ordered_periods)
    max_points = 40 if quarterly_mode else 10
    if len(trend_df) > max_points:
        trend_df = trend_df.tail(max_points)

    if quarterly_mode:
        st.caption("Quarterly attribute history (up to 10Y as available): Quality, Growth, Cash Flow")
    else:
        st.caption("Annual attribute history (5-10Y as available): Quality, Growth, Cash Flow")
    st.line_chart(trend_df)

    summary_cols = st.columns(3)

    def _summary_text(col_name: str) -> str:
        if col_name not in trend_df.columns:
            return "N/A"
        series = trend_df[col_name].dropna()
        if series.empty:
            return "N/A"
        latest = float(series.iloc[-1])
        lookback = 20 if quarterly_mode else 5
        if len(series) >= lookback:
            delta = latest - float(series.iloc[-lookback])
            return f"Latest {latest:+.1f} | 5Y Δ {delta:+.1f}"
        return f"Latest {latest:+.1f}"

    with summary_cols[0]:
        st.caption(f"Quality: {_summary_text('Quality')}")
    with summary_cols[1]:
        st.caption(f"Growth: {_summary_text('Growth')}")
    with summary_cols[2]:
        st.caption(f"Cash Flow: {_summary_text('Cash Flow')}")

    _pane_end()


def _render_workbench_styles(panel_min_height: str) -> None:
    st.markdown(
        """
        <style>
        .sr-workbench {
            border: 1px solid rgba(128, 128, 128, 0.28);
            border-radius: 0.68rem;
            padding: 0.42rem 0.5rem;
            min-height: __PANEL_MIN_HEIGHT__;
            background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
        }
        .sr-hero {
            border: 1px solid rgba(128, 128, 128, 0.22);
            border-radius: 0.52rem;
            padding: 0.34rem 0.42rem;
            margin-bottom: 0.34rem;
            background: rgba(255,255,255,0.02);
        }
        .sr-hero-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.22rem;
        }
        .sr-hero-item {
            border: 1px solid rgba(128, 128, 128, 0.18);
            border-radius: 0.42rem;
            padding: 0.2rem 0.28rem;
            background: rgba(255,255,255,0.015);
        }
        .sr-hero-label {
            font-size: clamp(0.52rem, 0.58vw, 0.58rem);
            line-height: 1.0;
            opacity: 0.72;
            margin-bottom: 0.06rem;
        }
        .sr-hero-value {
            font-size: clamp(0.72rem, 0.9vw, 0.8rem);
            line-height: 1.08;
            font-weight: 700;
        }
        .sr-pane {
            border: 1px solid rgba(128, 128, 128, 0.22);
            border-radius: 0.5rem;
            padding: 0.28rem 0.34rem;
            margin-bottom: 0.28rem;
            background: rgba(255,255,255,0.015);
        }
        .sr-pane-title {
            font-size: 0.66rem;
            text-transform: uppercase;
            letter-spacing: 0.02em;
            margin-bottom: 0.16rem;
            opacity: 0.82;
            font-weight: 700;
        }
        .sr-details-card {
            border: 1px solid rgba(128, 128, 128, 0.15);
            border-radius: 0.45rem;
            padding: 0.2rem 0.32rem;
            min-height: 2.05rem;
            margin-bottom: 0.24rem;
            background: rgba(255, 255, 255, 0.01);
        }
        .sr-details-label {
            font-size: clamp(0.58rem, 0.75vw, 0.66rem);
            line-height: 1.05;
            opacity: 0.78;
            margin-bottom: 0.08rem;
        }
        .sr-details-value {
            font-size: clamp(0.78rem, 1.15vw, 0.98rem);
            line-height: 1.05;
            font-weight: 700;
        }
        .sr-details-explain {
            font-size: clamp(0.52rem, 0.62vw, 0.58rem);
            line-height: 1.12;
            opacity: 0.72;
            margin-top: 0.07rem;
        }
        .sr-details-value.sr-good {
            color: #4ecb71;
        }
        .sr-details-value.sr-moderate {
            color: #f2c94c;
        }
        .sr-details-value.sr-weak {
            color: #ff6b6b;
        }
        .sr-score-row {
            margin-bottom: 0.16rem;
        }
        .sr-score-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.04rem;
        }
        .sr-score-label {
            font-size: 0.6rem;
            opacity: 0.75;
        }
        .sr-score-value {
            font-size: 0.62rem;
            font-weight: 700;
            opacity: 0.86;
        }
        .sr-score-track {
            width: 100%;
            height: 0.34rem;
            background: rgba(255,255,255,0.08);
            border-radius: 999px;
            overflow: hidden;
        }
        .sr-score-fill {
            height: 100%;
            border-radius: 999px;
        }
        .sr-open-primary button {
            border: 1px solid rgba(78, 203, 113, 0.55) !important;
            background: linear-gradient(180deg, rgba(78,203,113,0.22), rgba(78,203,113,0.1)) !important;
            font-weight: 650 !important;
        }
        .sr-criteria-row {
            display: flex;
            align-items: stretch;
            gap: 0;
            margin-bottom: 0.28rem;
        }
        .sr-criteria-score-panel {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 0.5rem;
            padding: 0.42rem 0.5rem;
            background: rgba(255,255,255,0.02);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            min-height: 4.5rem;
        }
        .sr-criteria-spacer {
            min-height: 4.5rem;
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 0.5rem;
        }
        div[class*="st-key-sr-row-good-"] {
            border: 1px solid rgba(78, 203, 113, 0.44);
            border-radius: 0.6rem;
            padding: 0.22rem 0.26rem;
            margin-bottom: 0.3rem;
            background: linear-gradient(180deg, rgba(78, 203, 113, 0.14), rgba(78, 203, 113, 0.05));
        }
        div[class*="st-key-sr-row-moderate-"] {
            border: 1px solid rgba(242, 201, 76, 0.42);
            border-radius: 0.6rem;
            padding: 0.22rem 0.26rem;
            margin-bottom: 0.3rem;
            background: linear-gradient(180deg, rgba(242, 201, 76, 0.16), rgba(242, 201, 76, 0.06));
        }
        div[class*="st-key-sr-row-weak-"] {
            border: 1px solid rgba(255, 107, 107, 0.42);
            border-radius: 0.6rem;
            padding: 0.22rem 0.26rem;
            margin-bottom: 0.3rem;
            background: linear-gradient(180deg, rgba(255, 107, 107, 0.15), rgba(255, 107, 107, 0.05));
        }
        .sr-criteria-score-label {
            font-size: 0.62rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            opacity: 0.75;
            font-weight: 700;
            margin-bottom: 0.18rem;
        }
        .sr-criteria-score-value {
            font-size: clamp(1rem, 2.2vw, 1.6rem);
            font-weight: 700;
            line-height: 1.0;
            margin-bottom: 0.18rem;
        }
        @media (max-width: 1200px) {
            .sr-hero-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .sr-details-value {
                font-size: 0.9rem;
            }
            .sr-criteria-score-value {
                font-size: 1.2rem;
            }
        }
        @media (max-width: 900px) {
            .sr-workbench {
                padding: 0.34rem 0.38rem;
            }
            .sr-pane {
                padding: 0.24rem 0.28rem;
            }
            .sr-details-card {
                min-height: 1.9rem;
            }
            .sr-criteria-score-panel {
                min-height: 3.8rem;
            }
        }
        @media (max-width: 640px) {
            .sr-hero-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .sr-criteria-score-label {
                font-size: 0.56rem;
            }
            .sr-criteria-score-value {
                font-size: 1rem;
            }
            .sr-details-value {
                font-size: 0.78rem;
            }
            .sr-details-explain {
                font-size: 0.5rem;
            }
        }
        </style>
        """.replace("__PANEL_MIN_HEIGHT__", panel_min_height),
        unsafe_allow_html=True,
    )


def render_context_html_card(title: str, rows: list[tuple[str, str]], subtitle: str | None = None) -> None:
    st.markdown(
        """
        <style>
        .stock-context-card {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 0.6rem;
            padding: 0.55rem 0.65rem;
            min-height: %s;
            background: rgba(255, 255, 255, 0.02);
        }
        .stock-context-title {
            font-size: 0.92rem;
            line-height: 1.2;
            font-weight: 700;
            margin-bottom: 0.22rem;
        }
        .stock-context-subtitle {
            font-size: 0.68rem;
            line-height: 1.15;
            opacity: 0.78;
            margin-bottom: 0.5rem;
        }
        .stock-context-row {
            margin-bottom: 0.45rem;
        }
        .stock-context-label {
            font-size: 0.62rem;
            line-height: 1.05;
            opacity: 0.72;
            margin-bottom: 0.08rem;
        }
        .stock-context-value {
            font-size: 0.78rem;
            line-height: 1.22;
            font-weight: 600;
            word-break: break-word;
        }
        .stock-context-section {
            border: 1px solid rgba(128, 128, 128, 0.2);
            border-radius: 0.45rem;
            padding: 0.38rem 0.45rem;
            margin-bottom: 0.42rem;
            background: rgba(255, 255, 255, 0.015);
        }
        .stock-context-section-title {
            font-size: 0.64rem;
            line-height: 1.05;
            text-transform: uppercase;
            letter-spacing: 0.02em;
            opacity: 0.76;
            margin-bottom: 0.22rem;
            font-weight: 700;
        }
        </style>
        """ % f"{FAVORITES_PANEL_MIN_HEIGHT_REM:.1f}rem",
        unsafe_allow_html=True,
    )

    rows_html = "".join(
        (
            f'<div class="stock-context-row" title="{_tooltip_attr(label)}">'
            f'<div class="stock-context-label">{html.escape(label)}</div>'
            f'<div class="stock-context-value">{html.escape(value)}</div>'
            "</div>"
        )
        for label, value in rows
    )
    subtitle_html = (
        f'<div class="stock-context-subtitle">{html.escape(subtitle)}</div>' if subtitle else ""
    )
    st.markdown(
        (
            '<div class="stock-context-card">'
            f'<div class="stock-context-title">{html.escape(title)}</div>'
            f"{subtitle_html}"
            f"{rows_html}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_structured_context_card(
    title: str,
    sections: list[tuple[str, list[tuple[str, str]]]],
    subtitle: str | None = None,
    sources: list[str] | None = None,
    two_col_sections: bool = False,
) -> None:
    st.markdown(
        """
        <style>
        .stock-context-card {
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 0.6rem;
            padding: 0.55rem 0.65rem;
            min-height: %s;
            background: rgba(255, 255, 255, 0.02);
        }
        .stock-context-title {
            font-size: 0.92rem;
            line-height: 1.2;
            font-weight: 700;
            margin-bottom: 0.22rem;
        }
        .stock-context-subtitle {
            font-size: 0.68rem;
            line-height: 1.15;
            opacity: 0.78;
            margin-bottom: 0.5rem;
        }
        .stock-context-section {
            border: 1px solid rgba(128, 128, 128, 0.2);
            border-radius: 0.45rem;
            padding: 0.38rem 0.45rem;
            margin-bottom: 0.42rem;
            background: rgba(255, 255, 255, 0.015);
        }
        .stock-context-section-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.42rem;
            margin-bottom: 0.42rem;
        }
        .stock-context-section-title {
            font-size: 0.64rem;
            line-height: 1.05;
            text-transform: uppercase;
            letter-spacing: 0.02em;
            opacity: 0.76;
            margin-bottom: 0.22rem;
            font-weight: 700;
        }
        .stock-context-row {
            margin-bottom: 0.3rem;
        }
        .stock-context-label {
            font-size: 0.62rem;
            line-height: 1.05;
            opacity: 0.72;
            margin-bottom: 0.06rem;
        }
        .stock-context-value {
            font-size: 0.77rem;
            line-height: 1.2;
            font-weight: 600;
            word-break: break-word;
        }
        </style>
        """ % f"{FAVORITES_PANEL_MIN_HEIGHT_REM:.1f}rem",
        unsafe_allow_html=True,
    )

    section_html: list[str] = []
    for section_title, section_rows in sections:
        rows_html = "".join(
            (
                f'<div class="stock-context-row" title="{_tooltip_attr(label)}">'
                f'<div class="stock-context-label">{html.escape(label)}</div>'
                f'<div class="stock-context-value">{html.escape(value)}</div>'
                "</div>"
            )
            for label, value in section_rows
        )
        section_html.append(
            (
                '<div class="stock-context-section">'
                f'<div class="stock-context-section-title">{html.escape(section_title)}</div>'
                f"{rows_html}"
                "</div>"
            )
        )

    subtitle_html = (
        f'<div class="stock-context-subtitle">{html.escape(subtitle)}</div>' if subtitle else ""
    )
    sources_rows = []
    for idx, src in enumerate(sources or [], start=1):
        sources_rows.append((f"Source {idx}", src))
    if sources_rows:
        sources_html = "".join(
            (
                f'<div class="stock-context-row" title="{_tooltip_attr(label, 'Reference source used to derive this insight.')}">'
                f'<div class="stock-context-label">{html.escape(label)}</div>'
                f'<div class="stock-context-value">{html.escape(value)}</div>'
                "</div>"
            )
            for label, value in sources_rows
        )
        section_html.append(
            (
                '<div class="stock-context-section">'
                '<div class="stock-context-section-title">Sources</div>'
                f"{sources_html}"
                "</div>"
            )
        )

    body_html = "".join(section_html)
    if two_col_sections and len(section_html) >= 2:
        lead = section_html[:2]
        trail = section_html[2:]
        body_html = '<div class="stock-context-section-grid">' + "".join(lead) + "</div>" + "".join(trail)

    st.markdown(
        (
            '<div class="stock-context-card">'
            f'<div class="stock-context-title">{html.escape(title)}</div>'
            f"{subtitle_html}"
            f"{body_html}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_macro_context_card(
    metrics: dict[str, object],
    macro: dict[str, str | float],
    recent: dict[str, object] | None = None,
) -> None:
    rating_rows = [
        ("Analyst Rating", str((recent or {}).get("rating_label", "N/A"))),
        ("Rating Detail", str((recent or {}).get("rating_detail", "No analyst snapshot"))),
        (
            "MRSI vs Industry",
            f"{float((recent or {}).get('mrsi_pct', 0.0)):+.1f}% vs {(recent or {}).get('industry_name', 'industry')} · {(recent or {}).get('mrsi_label', 'No Signal')}",
        ),
    ]
    sections = [
        (
            "Liquidity Shift",
            [
                ("Context", str(metrics.get("liq_context", "No Signal"))),
                ("Flow Trend (3M)", f"{metrics.get('liq_trend_3m_pct', 0):+.1f}%"),
                ("Flow Trend (6M)", f"{metrics.get('liq_trend_6m_pct', 0):+.1f}%"),
                ("Weekly Acceleration", f"{metrics.get('liq_accel_weekly_pct', 0):+.1f}%"),
                ("Flow Ratio", f"{metrics.get('volume_ratio_20_60', 0):.2f}x"),
            ],
        ),
        (
            "Macro Impact",
            [
                ("Impact", str(macro.get("macro_context", "No Signal"))),
                ("Driver", str(macro.get("macro_driver", "N/A"))),
                ("Beta Profile", str(macro.get("macro_beta_hint", "N/A"))),
                ("Market Regime (3M)", str(macro.get("macro_regime", "N/A"))),
            ],
        ),
        ("Ratings & Relative Strength", rating_rows),
    ]
    render_structured_context_card(
        "Macro Context",
        sections,
        subtitle="Liquidity and economic sensitivity snapshot",
        two_col_sections=True,
    )


def render_recent_information_card(recent: dict[str, object]) -> None:
    news_rows: list[tuple[str, str]] = []
    news_items = recent.get("news_items", []) or []
    if news_items:
        for idx, item in enumerate(news_items[:3], start=1):
            news_rows.append(
                (
                    f"Headline {idx}",
                    f"[{item.get('topic', 'General')}] {item.get('title', '')} ({item.get('provider', 'News')})",
                )
            )
    else:
        news_rows.append(("Recent Headlines", "No recent headlines available."))

    render_structured_context_card(
        "Recent Information",
        sections=[("News Feed", news_rows)],
        subtitle="Latest analyst and news context",
    )


def render_stock_details_panel(
    metrics: dict[str, object],
    company_name: str,
    ticker: str,
    universe: str,
    sector: str,
    industry: str,
    show_liquidity_context: bool,
    show_full_details: bool,
    favorite_label: str,
    favorite_button_key: str,
    on_toggle: Callable[..., Any],
    on_toggle_args: tuple[Any, ...],
    detail_section: str = "full",
) -> None:
    """Render a stock intelligence workbench.

    detail_section:
      "full"   – header + hero stats + criteria grid (default, used in card grid)
      "header" – company name + hero stats only (dedicated view top-row right column)
      "body"   – criteria grid + trend lenses only (dedicated view full-width section)
    """

    ticker_label = ticker.upper()
    price = _safe_float(metrics.get("latest"))
    change_20d = _safe_float(metrics.get("change_20d_pct"))
    vol_20d = _safe_float(metrics.get("volatility_20d"))
    beta = _safe_float(metrics.get("beta"))

    sales_yoy = _safe_float(metrics.get("revenue_growth_yoy"))
    eps_yoy = _safe_float(metrics.get("earnings_growth_yoy"))
    pe_ratio = _safe_float(metrics.get("pe_ratio"))
    fwd_pe = _safe_float(metrics.get("forward_pe"))
    pb_ratio = _safe_float(metrics.get("pb_ratio"))
    ps_ratio = _safe_float(metrics.get("ps_ratio"))
    peg_ratio = _safe_float(metrics.get("peg_ratio"))
    ev_ebitda = _safe_float(metrics.get("ev_ebitda"))

    gross_margin = _safe_float(metrics.get("gross_margin"))
    operating_margin = _safe_float(metrics.get("operating_margin"))
    roce = _safe_float(metrics.get("roce"))
    fcf_margin = _safe_float(metrics.get("fcf_margin"))
    fcf_yield = _safe_float(metrics.get("fcf_yield"))

    risk_profile = _risk_profile(beta, vol_20d)
    context = {
        "ticker": ticker_label,
        "industry": industry,
        "beta": beta,
        "volatility_20d": vol_20d,
        "risk_profile": risk_profile,
        "industry_profile": _industry_profile(industry),
    }

    panel_min_height = f"{FAVORITES_PANEL_MIN_HEIGHT_REM:.1f}rem" if show_liquidity_context else "auto"

    _render_workbench_styles(panel_min_height)

    sales_yoy_pct = sales_yoy * 100 if sales_yoy is not None else None
    eps_yoy_pct = eps_yoy * 100 if eps_yoy is not None else None

    quality_metrics = [
        ("Gross Margin", gross_margin, f"{gross_margin:.1f}%" if gross_margin is not None else "N/A"),
        ("Operating Margin", operating_margin, f"{operating_margin:.1f}%" if operating_margin is not None else "N/A"),
        ("ROCE", roce, f"{roce:.1f}%" if roce is not None else "N/A"),
        ("P/E", pe_ratio, f"{pe_ratio:.2f}" if pe_ratio is not None else "N/A"),
        ("Forward P/E", fwd_pe, f"{fwd_pe:.2f}" if fwd_pe is not None else "N/A"),
        ("P/B", pb_ratio, f"{pb_ratio:.2f}" if pb_ratio is not None else "N/A"),
    ]
    growth_metrics = [
        ("Sales YoY", sales_yoy_pct, f"+{sales_yoy_pct:.1f}%" if sales_yoy_pct is not None else "N/A"),
        ("EPS YoY", eps_yoy_pct, f"+{eps_yoy_pct:.1f}%" if eps_yoy_pct is not None else "N/A"),
        ("P/S", ps_ratio, f"{ps_ratio:.2f}" if ps_ratio is not None else "N/A"),
        ("PEG", peg_ratio, f"{peg_ratio:.2f}" if peg_ratio is not None else "N/A"),
    ]
    cashflow_metrics = [
        ("FCF Margin", fcf_margin, f"{fcf_margin:.1f}%" if fcf_margin is not None else "N/A"),
        ("FCF Yield", fcf_yield, f"{fcf_yield:.2f}%" if fcf_yield is not None else "N/A"),
        ("EV/EBITDA", ev_ebitda, f"{ev_ebitda:.2f}" if ev_ebitda is not None else "N/A"),
    ]

    quality_score = _section_score(quality_metrics, context)
    growth_score = _section_score(growth_metrics, context)
    cashflow_score = _section_score(cashflow_metrics, context)

    risk_base = 85.0 if risk_profile == "low" else 68.0 if risk_profile == "moderate" else 45.0
    rr = _safe_float(metrics.get("risk_reward"))
    if rr is not None:
        risk_base = max(0.0, min(100.0, risk_base + rr * 8.0))
    risk_score = risk_base
    composite_score = (quality_score + growth_score + cashflow_score + risk_score) / 4.0

    regime_label = "Risk-On" if (change_20d is not None and change_20d >= 0) else "Risk-Off"
    trend_status = "good" if regime_label == "Risk-On" else "weak"
    price_txt = f"${price:.2f}" if price is not None else "N/A"
    change_txt = f"{change_20d:+.1f}%" if change_20d is not None else "N/A"
    vol_txt = f"{vol_20d:.1f}%" if vol_20d is not None else "N/A"
    rr_txt = f"{rr:+.2f}" if rr is not None else "N/A"

    # ── header section: company name + hero stats ─────────────────────────────
    if detail_section in ("full", "header"):
        _render_stock_header(
            company_name,
            ticker,
            sector,
            industry,
            favorite_label,
            favorite_button_key,
            on_toggle,
            on_toggle_args,
            show_full_details,
        )

        if not show_full_details:
            _render_compact_stock_panel(
                universe,
                ticker,
                composite_score,
                quality_score,
                growth_score,
                cashflow_score,
                risk_score,
            )
            return

        st.markdown(
            (
                '<div class="sr-hero">'
                '<div class="sr-hero-grid">'
                f'<div class="sr-hero-item" title="{_tooltip_attr("Price")}">'
                '<div class="sr-hero-label">Price</div>'
                f'<div class="sr-hero-value">{price_txt}</div>'
                "</div>"
                f'<div class="sr-hero-item" title="{_tooltip_attr("20D Change")}">'
                '<div class="sr-hero-label">20D Change</div>'
                f'<div class="sr-hero-value" style="color:{_status_color("good" if (change_20d or 0) >= 0 else "weak")};">{change_txt}</div>'
                "</div>"
                f'<div class="sr-hero-item" title="{_tooltip_attr("Volatility")}">'
                '<div class="sr-hero-label">Volatility</div>'
                f'<div class="sr-hero-value">{vol_txt}</div>'
                "</div>"
                f'<div class="sr-hero-item" title="{_tooltip_attr("Regime")}">'
                '<div class="sr-hero-label">Regime</div>'
                f'<div class="sr-hero-value" style="color:{_status_color(trend_status)};">{regime_label}</div>'
                "</div>"
                "</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )

        if detail_section == "header":
            return

    if not show_full_details:
        return  # "body" mode with compact panel — nothing extra to render

    # ── body section: full-width criteria grid + trend lenses ─────────────────
    st.markdown('<div class="sr-workbench">', unsafe_allow_html=True)

    # ── Full-width criteria grid: one row per scorecard category ───────────────
    _render_criteria_row("Quality", quality_score, quality_metrics, context)
    _render_criteria_row("Growth", growth_score, growth_metrics, context)
    _render_criteria_row("Cash Flow", cashflow_score, cashflow_metrics, context)

    fund_pct = (quality_score + growth_score + cashflow_score) / 3.0
    ra_pct = (risk_score + quality_score) / 2.0
    _render_criteria_row(
        "Risk",
        risk_score,
        [],
        context,
        extra_cards=[
            (
                "Risk/Reward",
                rr_txt,
                "good" if (rr is not None and rr >= 0.7) else "moderate" if (rr is not None and rr >= 0.25) else "weak",
                "Expected return divided by expected volatility over the recent lookback.",
                "Higher is better; below 0.25 indicates weak risk-adjusted trend.",
            ),
            (
                "Beta",
                f"{beta:.2f}" if beta is not None else "N/A",
                "good" if (beta is not None and beta <= 1.1) else "moderate" if (beta is not None and beta <= 1.4) else "weak",
                "Beta measures sensitivity to broad market moves.",
                "Near 1.0 is balanced; much above 1.4 implies higher market sensitivity.",
            ),
            (
                "Volatility 20D",
                vol_txt,
                "good" if (vol_20d is not None and vol_20d <= 2.0) else "moderate" if (vol_20d is not None and vol_20d <= 3.5) else "weak",
                "20-day historical volatility (annualised).",
                "Low (<2%) = stable; high (>3.5%) = elevated risk.",
            ),
        ],
    )
    _render_criteria_row(
        "Composite",
        composite_score,
        [],
        context,
        extra_cards=[
            (
                "20D Change",
                change_txt,
                trend_status,
                "20-day price change as a percentage.",
                "Positive indicates recent upward momentum.",
            ),
            (
                "Fundamental %ile",
                f"{fund_pct:.0f}",
                "good" if fund_pct >= 75 else "moderate" if fund_pct >= 45 else "weak",
                "Average of Quality, Growth and Cash Flow scores.",
                "Relative fundamental strength across all scored metrics.",
            ),
            (
                "Risk-Adjusted %ile",
                f"{ra_pct:.0f}",
                "good" if ra_pct >= 75 else "moderate" if ra_pct >= 45 else "weak",
                "Blend of Risk and Quality scores.",
                "High values indicate strong fundamentals with manageable risk.",
            ),
        ],
    )

    _render_trend_lenses_pane(metrics)

    st.markdown('</div>', unsafe_allow_html=True)
