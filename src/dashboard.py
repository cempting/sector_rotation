
import streamlit as st

from .cache import clear_tickers_cache
from .constants import SECTOR_GRID_COLS, SECTORS
from .renderers import (
    _render_sector_industry_summary,
    render_industry_dashboard,
    render_industry_stock_page,
    render_sector_card,
)
from .universe import (
    get_universe_industries,
    get_universe_sectors,
    get_universe_tickers,
    list_universes,
)

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
</style>
"""


# ── nav callbacks ─────────────────────────────────────────────────────────────

def _on_universe_change() -> None:
    st.session_state.view = "sector"
    for k in ("selected_sector", "selected_industry", "nav_sector", "nav_industry"):
        st.session_state.pop(k, None)


def _on_sector_change() -> None:
    val = st.session_state.get("nav_sector", "— all sectors —")
    if val == "— all sectors —":
        st.session_state.view = "sector"
        st.session_state.pop("selected_sector", None)
        st.session_state.pop("selected_industry", None)
    else:
        st.session_state.view = "industry"
        st.session_state.selected_sector = val
        st.session_state.pop("selected_industry", None)
    st.session_state.pop("nav_industry", None)


def _on_industry_change() -> None:
    val = st.session_state.get("nav_industry", "— all industries —")
    if val == "— all industries —":
        st.session_state.view = "industry"
        st.session_state.pop("selected_industry", None)
    else:
        st.session_state.view = "industry_stocks"
        st.session_state.selected_industry = val


# ── top-nav bar ───────────────────────────────────────────────────────────────

def _render_top_nav() -> str:
    """Render the sticky top navigation bar; returns selected_universe."""
    st.markdown('<div class="top-nav">', unsafe_allow_html=True)

    universes = list_universes()
    view = st.session_state.get("view", "sector")
    sector_nav = st.session_state.get("selected_sector")
    industry_nav = st.session_state.get("selected_industry")

    # ── one-row selectors: Universe · Sector · Industry · Refresh ────────────
    nav_universe_col, nav_sector_col, nav_industry_col, nav_refresh_col = st.columns([3, 3, 3, 1])

    with nav_universe_col:
        selected_universe = st.selectbox(
            "Universe", universes,
            key="nav_universe",
            on_change=_on_universe_change,
            label_visibility="collapsed",
        )
    st.session_state.selected_universe = selected_universe

    csv_sectors = get_universe_sectors(selected_universe)
    sector_options = ["— all sectors —"] + csv_sectors
    current_sector = st.session_state.get("selected_sector", "— all sectors —")
    st.session_state["nav_sector"] = current_sector if current_sector in sector_options else "— all sectors —"

    with nav_sector_col:
        st.selectbox(
            "Sector", sector_options,
            key="nav_sector",
            on_change=_on_sector_change,
            label_visibility="collapsed",
        )

    with nav_industry_col:
        current_sector_val = st.session_state.get("nav_sector", "— all sectors —")
        if current_sector_val != "— all sectors —":
            csv_industries = get_universe_industries(selected_universe, current_sector_val)
            industry_options = ["— all industries —"] + csv_industries
            current_industry = st.session_state.get("selected_industry", "— all industries —")
            st.session_state["nav_industry"] = current_industry if current_industry in industry_options else "— all industries —"
            st.selectbox(
                "Industry", industry_options,
                key="nav_industry",
                on_change=_on_industry_change,
                label_visibility="collapsed",
            )
        else:
            st.selectbox(
                "Industry", ["— all industries —"],
                disabled=True,
                label_visibility="collapsed",
            )

    with nav_refresh_col:
        if view == "industry_stocks" and sector_nav and industry_nav:
            refresh_tickers = get_universe_tickers(selected_universe, sector=sector_nav, industry=industry_nav)
        elif view == "industry" and sector_nav:
            refresh_tickers = get_universe_tickers(selected_universe, sector=sector_nav)
        else:
            refresh_tickers = get_universe_tickers(selected_universe)

        if st.button("\U0001f504", key="nav_refresh", help="Refresh live data", use_container_width=True):
            clear_tickers_cache(refresh_tickers)
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    return selected_universe


# ── main ──────────────────────────────────────────────────────────────────────

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

    # ── content ───────────────────────────────────────────────────────────────
    view = st.session_state.get("view", "sector")

    if (
        view == "industry_stocks"
        and "selected_sector" in st.session_state
        and "selected_industry" in st.session_state
    ):
        render_industry_stock_page(
            st.session_state.selected_sector,
            st.session_state.selected_industry,
        )
    elif view == "industry" and "selected_sector" in st.session_state:
        render_industry_dashboard(st.session_state.selected_sector)
    else:
        universe_sectors = get_universe_sectors(selected_universe)
        cols = st.columns(SECTOR_GRID_COLS)
        for i, sector_name in enumerate(universe_sectors):
            with cols[i % SECTOR_GRID_COLS]:
                etf_ticker = SECTORS.get(sector_name)
                if not etf_ticker:
                    from .constants import SECTOR_NAME_MAP
                    for short, long_name in SECTOR_NAME_MAP.items():
                        if long_name == sector_name:
                            etf_ticker = SECTORS.get(short)
                            break
                if etf_ticker:
                    render_sector_card(sector_name, etf_ticker)
                else:
                    _render_universe_sector_card(selected_universe, sector_name)


def _render_universe_sector_card(universe: str, sector: str) -> None:
    """Render a sector card for a universe sector that has no ETF mapping."""
    st.subheader(sector)
    _render_sector_industry_summary(universe, sector)
    if st.button("View Industries", key=f"universe-sector-{universe}-{sector}"):
        st.session_state.view = "industry"
        st.session_state.selected_sector = sector
        st.session_state.pop("selected_industry", None)
        st.rerun()


if __name__ == "__main__":
    main()
