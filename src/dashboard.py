import streamlit as st

from .core.data import list_universes
from .core.data.cache import clear_tickers_cache
from .core.data.download_status import get_download_status, is_download_blocked
from .features import FeatureRegistry

_ROUTE_BY_FEATURE = {
    "browse": "sector_industry_stocks",
    "search": "search",
    "favorites": "favorites",
    "suggestions": "suggestions",
}

# ── mobile-friendly top-nav CSS ───────────────────────────────────────────────
_TOP_NAV_CSS = """
<style>
/* hide default sidebar toggle and sidebar */
[data-testid="collapsedControl"] { display: none !important; }
section[data-testid="stSidebar"] { display: none !important; }

/* remove Streamlit's default top spacing so controls sit at the top */
[data-testid="stAppViewContainer"] .main .block-container {
    padding-top: 0.2rem !important;
}

/* top-nav container */
.top-nav {
    position: sticky;
    top: 0;
    z-index: 999;
    background: var(--background-color, #0e1117);
    padding: 0.15rem 0 0.2rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 0.4rem;
}

/* compact selectbox labels */
.top-nav .stSelectbox label {
    font-size: 0.7rem !important;
    margin-bottom: 0 !important;
    opacity: 0.6;
}

/* tighter column gap inside the nav */
.top-nav [data-testid="column"] { padding: 0 0.25rem; }

/* smaller font for cards on narrow screens */
@media (max-width: 640px) {
    h2 { font-size: 1rem !important; }
    h3 { font-size: 0.9rem !important; }
    .stButton button { font-size: 0.8rem !important; padding: 0.3rem 0.5rem; }
}

/* favorites import/export row visual alignment */
.favorites-controls [data-testid="stFileUploader"] {
    max-width: 18rem;
}

.favorites-controls .stButton button,
.favorites-controls .stDownloadButton button {
    min-height: 2.35rem;
}

.favorites-controls [data-testid="stFileUploaderDropzone"] {
    min-height: 2.35rem;
    padding-top: 0.3rem;
    padding-bottom: 0.3rem;
}

.favorites-controls [data-testid="stCheckbox"] {
    padding-top: 0.35rem;
}
</style>
"""


def _feature_for_view(view: str) -> str:
    if view in {"favorites", "search", "suggestions", "liquidity"}:
        if view == "liquidity":
            return "suggestions"
        return view
    return "browse"


def _set_view_for_feature(feature: str) -> None:
    if feature == "favorites":
        st.session_state.view = "favorites"
    elif feature == "search":
        st.session_state.view = "search"
    elif feature == "suggestions":
        st.session_state.view = "suggestions"
    else:
        st.session_state.view = "sector"


def _open_search_view() -> None:
    query = st.session_state.get("nav_search_query", "").strip()
    if not query:
        return
    st.session_state.search_query = query
    st.session_state.nav_feature = "search"
    st.session_state.view = "search"


def _render_top_nav() -> str:
    """Render the sticky top navigation bar; returns selected_universe."""
    st.markdown('<div class="top-nav">', unsafe_allow_html=True)

    all_universes = list_universes()
    if "nav_universe" not in st.session_state or st.session_state.get("nav_universe") not in all_universes:
        st.session_state["nav_universe"] = all_universes[0] if all_universes else ""

    current_feature = _feature_for_view(st.session_state.get("view", "sector"))
    nav_feature = st.session_state.get("nav_feature", current_feature)
    if nav_feature not in _ROUTE_BY_FEATURE:
        nav_feature = current_feature
    st.session_state["nav_feature"] = nav_feature

    # Row 1: feature selector + refresh
    feature_col, refresh_col = st.columns([9, 1])

    with feature_col:
        labels = {
            name: FeatureRegistry.get_feature(route).get_nav_label()
            for name, route in _ROUTE_BY_FEATURE.items()
        }
        selected_feature = st.radio(
            "Feature",
            list(_ROUTE_BY_FEATURE.keys()),
            index=list(_ROUTE_BY_FEATURE.keys()).index(nav_feature),
            key="nav_feature",
            horizontal=True,
            label_visibility="collapsed",
            format_func=lambda mode: labels[mode],
        )
        if selected_feature != current_feature:
            _set_view_for_feature(selected_feature)

    active_feature = st.session_state.get("nav_feature", "browse")
    active_route = _ROUTE_BY_FEATURE[active_feature]
    feature = FeatureRegistry.get_feature(active_route)

    selected_universe = st.session_state.get("selected_universe") or st.session_state.get("nav_universe") or ""
    selected_universe = feature.render_nav_controls(selected_universe)
    st.session_state.selected_universe = selected_universe

    with refresh_col:
        if st.button("🔄", key="nav_refresh", help="Refresh live data", use_container_width=True):
            if is_download_blocked("yfinance"):
                st.warning("Refresh is temporarily blocked due to Yahoo Finance rate limits.")
                st.rerun()
            refresh_tickers = feature.get_refresh_tickers(selected_universe)
            clear_tickers_cache(refresh_tickers)
            on_manual_refresh = getattr(feature, "on_manual_refresh", None)
            if callable(on_manual_refresh):
                on_manual_refresh(selected_universe)
            st.rerun()

    status = get_download_status(max_age_seconds=3600)
    if status:
        level = str(status.get("level", "ok"))
        message = str(status.get("message", ""))
        icon = "✅"
        if level == "rate_limited":
            icon = "⛔"
            retry_after = int(status.get("retry_after_seconds", 0) or 0)
            if retry_after > 0:
                message = f"{message} Retry in about {max(1, retry_after // 60)} min."
        elif level == "warning":
            icon = "⚠️"
        elif level == "error":
            icon = "❌"
        st.caption(f"{icon} Data status: {message}")

    st.markdown('</div>', unsafe_allow_html=True)
    return selected_universe


def main() -> None:
    st.set_page_config(
        page_title="Sector Screener",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(_TOP_NAV_CSS, unsafe_allow_html=True)

    if "view" not in st.session_state:
        st.session_state.view = "sector"

    selected_universe = _render_top_nav()

    active_feature = st.session_state.get("nav_feature", _feature_for_view(st.session_state.get("view", "sector")))
    active_route = _ROUTE_BY_FEATURE.get(active_feature, "sector_industry_stocks")
    feature = FeatureRegistry.get_feature(active_route)
    FeatureRegistry.render_route(active_route, **feature.get_render_kwargs(selected_universe))


if __name__ == "__main__":
    main()
