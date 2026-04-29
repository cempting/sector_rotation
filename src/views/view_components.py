import html
from collections.abc import Callable
from typing import Any

import pandas as pd
import streamlit as st

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
            '<div class="stock-context-row">'
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
                '<div class="stock-context-row">'
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
                '<div class="stock-context-row">'
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
    sector: str,
    industry: str,
    show_liquidity_context: bool,
    favorite_label: str,
    favorite_button_key: str,
    on_toggle: Callable[..., Any],
    on_toggle_args: tuple[Any, ...],
) -> None:
    """Render a compact 3-column details panel sized to sit beside the chart."""
    panel_min_height = f"{FAVORITES_PANEL_MIN_HEIGHT_REM:.1f}rem" if show_liquidity_context else "auto"
    price = f"${metrics.get('latest', 0):.2f}"
    change = f"{metrics.get('change_20d_pct', 0):+.1f}%"
    detail_items = [
        ("Price", price, change),
        ("Vol (20D)", f"{metrics.get('volatility_20d', 0):.1f}%", ""),
        ("Exp Vol", f"{metrics.get('exp_vol_ann_pct', 0):.1f}%", "30D ann"),
        ("Exp Ret", f"{metrics.get('exp_return_ann_pct', 0):+.1f}%", "30D ann"),
        ("Risk/Reward", f"{metrics.get('risk_reward', 0):+.2f}", "ret/vol"),
        ("Market Cap", format_fundamental(metrics.get('market_cap')), ""),
        ("P/E", format_fundamental(metrics.get('pe_ratio')), ""),
        ("P/B", format_fundamental(metrics.get('pb_ratio')), ""),
        ("EPS (TTM)", format_fundamental(metrics.get('eps_trailing')), ""),
        ("ROE", format_fundamental(metrics.get('roe'), is_pct=True), ""),
        ("Div Yield", format_fundamental(metrics.get('dividend_yield'), is_pct=True), ""),
        ("Debt/Eq", format_fundamental(metrics.get('debt_to_equity')), ""),
    ]

    st.markdown(
        """
        <style>
        .stock-details-panel {
            display: block;
            min-height: %s;
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
        """ % panel_min_height,
        unsafe_allow_html=True,
    )

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

    cards = []
    for label, value, delta in detail_items:
        delta_html = f'<div class="stock-details-delta">{delta}</div>' if delta else ""
        cards.append(
            f'<div class="stock-details-card">'
            f'<div class="stock-details-label">{label}</div>'
            f'<div class="stock-details-value">{value}</div>'
            f"{delta_html}"
            "</div>"
        )

    st.markdown(
        (
            '<div class="stock-details-panel">'
            f'<div class="stock-details-grid">{"".join(cards)}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
