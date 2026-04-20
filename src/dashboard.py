import streamlit as st

from .constants import SECTOR_GRID_COLS, SECTORS
from .data import fetch_industry_counts
from .renderers import (
    render_industry_dashboard,
    render_industry_stock_page,
    render_sector_card,
)


def main() -> None:
    st.set_page_config(page_title="Sector Screener", layout="wide")

    if "view" not in st.session_state:
        st.session_state.view = "sector"

    with st.sidebar:
        st.header("Quick Navigation")

        sector_options = ["No selection"] + list(SECTORS.keys())
        selected_sector = st.selectbox(
            "Select Sector", sector_options, index=0, key="sidebar_selected_sector"
        )

        selected_industry = "No selection"
        if selected_sector != "No selection":
            industry_counts = fetch_industry_counts(selected_sector)
            industry_options = ["No selection"] + industry_counts.index.tolist()
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

    if st.session_state.view == "industry_stocks" and "selected_sector" in st.session_state and "selected_industry" in st.session_state:
        render_industry_stock_page(st.session_state.selected_sector, st.session_state.selected_industry)
    elif st.session_state.view == "industry" and "selected_sector" in st.session_state:
        render_industry_dashboard(st.session_state.selected_sector)
    else:
        st.title("Sector Screener - 2 Year Overview")
        cols = st.columns(SECTOR_GRID_COLS)
        for i, (name, ticker) in enumerate(SECTORS.items()):
            with cols[i % SECTOR_GRID_COLS]:
                render_sector_card(name, ticker)


if __name__ == "__main__":
    main()
