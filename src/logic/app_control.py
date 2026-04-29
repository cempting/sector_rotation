import streamlit as st


def open_industry_stocks(sector: str, industry: str) -> None:
    st.session_state.view = "industry_stocks"
    st.session_state.selected_sector = sector
    st.session_state.selected_industry = industry


def nav_to_industry_stocks_button(sector: str, industry: str, key: str | None = None) -> None:
    st.button(
        "View Stocks",
        key=key or f"stocks-{sector}-{industry}",
        on_click=open_industry_stocks,
        args=(sector, industry),
    )
