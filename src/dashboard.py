
import streamlit as st
from .constants import SECTOR_GRID_COLS, SECTORS
from .renderers import (
    render_industry_dashboard,
    render_industry_stock_page,
    render_sector_card,
)
from .cache import update_all_ticker_caches
from .universe import list_universes, get_universe_sectors, get_universe_industries


def _on_universe_change():
    """Reset navigation when user switches universe."""
    st.session_state.view = "sector"
    for k in ("selected_sector", "selected_industry",
              "sidebar_selected_sector", "sidebar_selected_industry"):
        st.session_state.pop(k, None)


def _on_sidebar_sector_change():
    """Navigate when user picks a sector in the sidebar."""
    val = st.session_state.get("sidebar_selected_sector", "No selection")
    if val == "No selection":
        st.session_state.view = "sector"
        st.session_state.pop("selected_sector", None)
        st.session_state.pop("selected_industry", None)
    else:
        st.session_state.view = "industry"
        st.session_state.selected_sector = val
        st.session_state.pop("selected_industry", None)
    # Reset industry widget for the new sector
    st.session_state.pop("sidebar_selected_industry", None)


def _on_sidebar_industry_change():
    """Navigate when user picks an industry in the sidebar."""
    val = st.session_state.get("sidebar_selected_industry", "No selection")
    if val == "No selection":
        st.session_state.view = "industry"
        st.session_state.pop("selected_industry", None)
    else:
        st.session_state.view = "industry_stocks"
        st.session_state.selected_industry = val


def main() -> None:
    st.set_page_config(page_title="Sector Screener", layout="wide")

    if "view" not in st.session_state:
        st.session_state.view = "sector"

    # Background cache update state
    if "cache_update_started" not in st.session_state:
        st.session_state.cache_update_started = False
    if "cache_update_progress" not in st.session_state:
        st.session_state.cache_update_progress = {"done": 0, "total": 0, "last": None}

    import threading
    def cache_progress(done, total, last):
        st.session_state.cache_update_progress = {"done": done, "total": total, "last": last}

    if not st.session_state.cache_update_started:
        thread = threading.Thread(target=update_all_ticker_caches, args=(cache_progress,), daemon=True)
        thread.start()
        st.session_state.cache_update_started = True

    with st.sidebar:
        st.header("Quick Navigation")

        # Universe selector
        universes = list_universes()
        selected_universe = st.selectbox(
            "Stock Universe", universes, key="sidebar_universe",
            on_change=_on_universe_change,
        )
        st.session_state.selected_universe = selected_universe

        # Cache status
        prog = st.session_state.cache_update_progress
        if prog["total"] > 0 and prog["done"] < prog["total"]:
            st.caption(f"Cache: {prog['done']}/{prog['total']} — {prog['last']}")
        elif prog["total"] > 0 and prog["done"] >= prog["total"]:
            st.success("Cache update complete!")

        # --- Sector dropdown ---
        csv_sectors = get_universe_sectors(selected_universe)
        sector_options = ["No selection"] + csv_sectors
        nav_sector = st.session_state.get("selected_sector", "No selection")

        # Force widget to match nav state before rendering
        st.session_state["sidebar_selected_sector"] = nav_sector if nav_sector in sector_options else "No selection"

        selected_sector = st.selectbox(
            "Select Sector", sector_options,
            key="sidebar_selected_sector",
            on_change=_on_sidebar_sector_change,
        )

        # --- Industry dropdown ---
        selected_industry = "No selection"
        if selected_sector != "No selection":
            csv_industries = get_universe_industries(selected_universe, selected_sector)
            industry_options = ["No selection"] + csv_industries
            nav_industry = st.session_state.get("selected_industry", "No selection")

            # Force widget to match nav state before rendering
            st.session_state["sidebar_selected_industry"] = nav_industry if nav_industry in industry_options else "No selection"

            selected_industry = st.selectbox(
                "Select Industry", industry_options,
                key="sidebar_selected_industry",
                on_change=_on_sidebar_industry_change,
            )

    # --- Content ---
    if st.session_state.view == "industry_stocks" and "selected_sector" in st.session_state and "selected_industry" in st.session_state:
        render_industry_stock_page(st.session_state.selected_sector, st.session_state.selected_industry)
    elif st.session_state.view == "industry" and "selected_sector" in st.session_state:
        render_industry_dashboard(st.session_state.selected_sector)
    else:
        selected_universe = st.session_state.get("selected_universe", "S&P 500")
        universe_sectors = get_universe_sectors(selected_universe)

        cols = st.columns(SECTOR_GRID_COLS)
        for i, sector_name in enumerate(universe_sectors):
            with cols[i % SECTOR_GRID_COLS]:
                etf_ticker = SECTORS.get(sector_name)
                if not etf_ticker:
                    from .constants import SECTOR_NAME_MAP
                    for short, long in SECTOR_NAME_MAP.items():
                        if long == sector_name:
                            etf_ticker = SECTORS.get(short)
                            break
                if etf_ticker:
                    render_sector_card(sector_name, etf_ticker)
                else:
                    _render_universe_sector_card(selected_universe, sector_name)


def _render_universe_sector_card(universe: str, sector: str) -> None:
    """Render a sector card for a universe sector that has no ETF."""
    from .universe import get_universe_industries
    industries = get_universe_industries(universe, sector)
    st.subheader(sector)
    st.caption(f"{len(industries)} industries")
    if st.button(f"View Industries", key=f"universe-sector-{universe}-{sector}"):
        st.session_state.view = "industry"
        st.session_state.selected_sector = sector
        st.session_state.pop("selected_industry", None)
        st.rerun()


if __name__ == "__main__":
    main()
