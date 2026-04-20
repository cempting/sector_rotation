
import streamlit as st
import time
from .constants import SECTOR_GRID_COLS, SECTORS
from .renderers import (
    render_industry_dashboard,
    render_industry_stock_page,
    render_sector_card,
)
from .cache import update_all_ticker_caches
from .universe import list_universes, get_universe_sectors, get_universe_industries


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
        selected_universe = st.selectbox("Stock Universe", universes, key="sidebar_universe")
        st.session_state.selected_universe = selected_universe

        # Show cache update status
        prog = st.session_state.cache_update_progress
        if prog["total"] > 0 and prog["done"] < prog["total"]:
            st.info(f"Background cache update: {prog['done']}/{prog['total']} tickers updated. Last: {prog['last']}")
        elif prog["total"] > 0 and prog["done"] >= prog["total"]:
            st.success("Background cache update complete!")
        else:
            st.caption("Cache update will run in the background.")

        # Sector dropdown driven by selected universe CSV
        csv_sectors = get_universe_sectors(selected_universe)
        sector_options = ["No selection"] + csv_sectors
        selected_sector = st.selectbox(
            "Select Sector", sector_options, index=0, key="sidebar_selected_sector"
        )

        # Industry dropdown driven by selected universe CSV + sector
        selected_industry = "No selection"
        if selected_sector != "No selection":
            csv_industries = get_universe_industries(selected_universe, selected_sector)
            industry_options = ["No selection"] + csv_industries
            selected_industry = st.selectbox(
                "Select Industry", industry_options, index=0, key="sidebar_selected_industry"
            )

        if st.button("Go to Selection"):
            if selected_sector == "No selection":
                st.session_state.view = "sector"
                st.session_state.pop("selected_sector", None)
                st.session_state.pop("selected_industry", None)
            elif selected_industry == "No selection":
                st.session_state.view = "industry"
                st.session_state.selected_sector = selected_sector
                st.session_state.pop("selected_industry", None)
            else:
                st.session_state.view = "industry_stocks"
                st.session_state.selected_sector = selected_sector
                st.session_state.selected_industry = selected_industry
            st.rerun()

    # Show cache update status in main header
    prog = st.session_state.cache_update_progress
    if prog["total"] > 0 and prog["done"] < prog["total"]:
        st.title(f"Sector Screener - 2 Year Overview  ")
        st.warning(f"Background cache update: {prog['done']}/{prog['total']} tickers updated. Last: {prog['last']}")
    elif prog["total"] > 0 and prog["done"] >= prog["total"]:
        st.title("Sector Screener - 2 Year Overview  ")
        st.success("Background cache update complete!")
    else:
        st.title("Sector Screener - 2 Year Overview")

    if st.session_state.view == "industry_stocks" and "selected_sector" in st.session_state and "selected_industry" in st.session_state:
        render_industry_stock_page(st.session_state.selected_sector, st.session_state.selected_industry)
    elif st.session_state.view == "industry" and "selected_sector" in st.session_state:
        render_industry_dashboard(st.session_state.selected_sector)
    else:
        # Show sector cards from the selected universe
        selected_universe = st.session_state.get("selected_universe", "S&P 500")
        universe_sectors = get_universe_sectors(selected_universe)

        # For sectors that have a matching ETF ticker in SECTORS, use the ETF chart.
        # Otherwise, show a simple sector card with name and industry count.
        cols = st.columns(SECTOR_GRID_COLS)
        for i, sector_name in enumerate(universe_sectors):
            with cols[i % SECTOR_GRID_COLS]:
                # Try to find a matching ETF ticker for this sector
                etf_ticker = SECTORS.get(sector_name)
                # Also check via the sector name map (e.g. "Information Technology" -> "Technology" -> "XLK")
                if not etf_ticker:
                    from .constants import SECTOR_NAME_MAP
                    # Reverse map: long name -> short name -> ETF
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
        st.rerun()


if __name__ == "__main__":
    main()
