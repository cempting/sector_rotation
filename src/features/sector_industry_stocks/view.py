"""Sector/Industry/Stocks browsing feature."""

import streamlit as st

from ...core.ui.interface import FeatureView
from ...core.data import (
    get_sector_industry_counts,
    get_universe_industries,
    get_universe_sector_stock_count,
    get_universe_sectors,
    get_universe_tickers,
    list_universes,
)
from .rendering import render_industry_dashboard, render_industry_stock_page, render_sector_grid


class SectorIndustryStocksView(FeatureView):
    """Feature for browsing and analyzing sectors, industries, and stocks."""

    def get_route_name(self) -> str:
        """Return the feature's unique route name."""
        return "sector_industry_stocks"

    def get_nav_label(self) -> str:
        return "Sector / Industry / Stocks"

    def render_nav_controls(self, selected_universe: str) -> str:
        universes = list_universes()
        if "nav_universe" not in st.session_state or st.session_state.get("nav_universe") not in universes:
            st.session_state["nav_universe"] = selected_universe if selected_universe in universes else universes[0]

        nav_universe_col, nav_sector_col, nav_industry_col, nav_stock_col = st.columns([3, 3, 3, 3])

        with nav_universe_col:
            new_universe = st.selectbox(
                "Universe",
                universes,
                key="nav_universe",
                label_visibility="collapsed",
            )

        if new_universe != selected_universe:
            st.session_state.pop("selected_sector", None)
            st.session_state.pop("selected_industry", None)
            st.session_state.pop("selected_stock", None)
            st.session_state.pop("nav_sector", None)
            st.session_state.pop("nav_industry", None)
            st.session_state.pop("nav_stock", None)
            st.session_state.view = "sector"
        st.session_state.selected_universe = new_universe

        csv_sectors = get_universe_sectors(new_universe)
        if not csv_sectors:
            st.session_state.pop("selected_sector", None)
            st.session_state.pop("nav_sector", None)
            st.session_state.view = "industry"

            with nav_sector_col:
                st.selectbox(
                    "Sector",
                    ["No sector breakdown"],
                    disabled=True,
                    label_visibility="collapsed",
                )

            csv_industries = get_universe_industries(new_universe, None)
            industry_options = ["— all industries —"] + csv_industries
            current_industry = st.session_state.get("selected_industry", "— all industries —")
            st.session_state["nav_industry"] = (
                current_industry if current_industry in industry_options else "— all industries —"
            )
            with nav_industry_col:
                selected_industry = st.selectbox(
                    "Industry",
                    industry_options,
                    key="nav_industry",
                    label_visibility="collapsed",
                )

            if selected_industry == "— all industries —":
                st.session_state.pop("selected_industry", None)
                st.session_state.pop("selected_stock", None)
                st.session_state.pop("nav_stock", None)
                st.session_state.view = "industry"
                with nav_stock_col:
                    st.selectbox(
                        "Stock",
                        ["— all stocks —"],
                        disabled=True,
                        label_visibility="collapsed",
                    )
            else:
                st.session_state.selected_industry = selected_industry
                industry_tickers = get_universe_tickers(new_universe, industry=selected_industry)
                stock_options = ["— all stocks —"] + industry_tickers
                current_stock = st.session_state.get("selected_stock", "— all stocks —")
                st.session_state["nav_stock"] = (
                    current_stock if current_stock in stock_options else "— all stocks —"
                )
                with nav_stock_col:
                    selected_stock = st.selectbox(
                        "Stock",
                        stock_options,
                        key="nav_stock",
                        label_visibility="collapsed",
                    )

                if selected_stock == "— all stocks —":
                    st.session_state.pop("selected_stock", None)
                else:
                    st.session_state.selected_stock = selected_stock
                st.session_state.view = "industry_stocks"

            return new_universe

        sector_options = ["— all sectors —"] + csv_sectors
        current_sector = st.session_state.get("selected_sector", "— all sectors —")
        st.session_state["nav_sector"] = current_sector if current_sector in sector_options else "— all sectors —"

        with nav_sector_col:
            sector_select_col, sector_info_col = st.columns([10, 1])
            with sector_select_col:
                selected_sector = st.selectbox(
                    "Sector",
                    sector_options,
                    key="nav_sector",
                    label_visibility="collapsed",
                )
            with sector_info_col:
                tooltip_details = self._sector_tooltip_details(new_universe, selected_sector)
                with st.popover("i", help="Show sector details", use_container_width=True):
                    if selected_sector and selected_sector != "— all sectors —":
                        st.markdown(f"**{selected_sector}**")
                    for detail in tooltip_details:
                        st.caption(detail)

        if selected_sector == "— all sectors —":
            st.session_state.pop("selected_sector", None)
            st.session_state.pop("selected_industry", None)
            st.session_state.pop("selected_stock", None)
            st.session_state.view = "sector"
            with nav_industry_col:
                st.selectbox(
                    "Industry",
                    ["— all industries —"],
                    disabled=True,
                    label_visibility="collapsed",
                )
            with nav_stock_col:
                st.selectbox(
                    "Stock",
                    ["— all stocks —"],
                    disabled=True,
                    label_visibility="collapsed",
                )
            return new_universe

        st.session_state.selected_sector = selected_sector
        st.session_state.view = "industry"

        csv_industries = get_universe_industries(new_universe, selected_sector)
        industry_options = ["— all industries —"] + csv_industries
        current_industry = st.session_state.get("selected_industry", "— all industries —")
        st.session_state["nav_industry"] = current_industry if current_industry in industry_options else "— all industries —"
        with nav_industry_col:
            selected_industry = st.selectbox(
                "Industry",
                industry_options,
                key="nav_industry",
                label_visibility="collapsed",
            )

        if selected_industry == "— all industries —":
            st.session_state.pop("selected_industry", None)
            st.session_state.pop("selected_stock", None)
            st.session_state.pop("nav_stock", None)
            st.session_state.view = "industry"
            with nav_stock_col:
                st.selectbox(
                    "Stock",
                    ["— all stocks —"],
                    disabled=True,
                    label_visibility="collapsed",
                )
        else:
            st.session_state.selected_industry = selected_industry
            industry_tickers = get_universe_tickers(
                new_universe,
                sector=selected_sector,
                industry=selected_industry,
            )
            stock_options = ["— all stocks —"] + industry_tickers
            current_stock = st.session_state.get("selected_stock", "— all stocks —")
            st.session_state["nav_stock"] = (
                current_stock if current_stock in stock_options else "— all stocks —"
            )

            with nav_stock_col:
                selected_stock = st.selectbox(
                    "Stock",
                    stock_options,
                    key="nav_stock",
                    label_visibility="collapsed",
                )

            if selected_stock == "— all stocks —":
                st.session_state.pop("selected_stock", None)
            else:
                st.session_state.selected_stock = selected_stock
            st.session_state.view = "industry_stocks"

        return new_universe

    def get_refresh_tickers(self, selected_universe: str) -> list[str]:
        view = st.session_state.get("view", "sector")
        sector = st.session_state.get("selected_sector")
        industry = st.session_state.get("selected_industry")

        if view == "industry_stocks" and sector and industry:
            selected_stock = st.session_state.get("selected_stock")
            if selected_stock:
                return [selected_stock]
            return get_universe_tickers(selected_universe, sector=sector, industry=industry)
        if view == "industry_stocks" and industry:
            selected_stock = st.session_state.get("selected_stock")
            if selected_stock:
                return [selected_stock]
            return get_universe_tickers(selected_universe, industry=industry)
        if view == "industry" and industry and not sector:
            return get_universe_tickers(selected_universe, industry=industry)
        if view == "industry" and sector:
            return get_universe_tickers(selected_universe, sector=sector)
        return get_universe_tickers(selected_universe)

    def get_render_kwargs(self, selected_universe: str) -> dict[str, str | None]:
        return {
            "universe": selected_universe,
            "sector": st.session_state.get("selected_sector"),
            "industry": st.session_state.get("selected_industry"),
            "stock": st.session_state.get("selected_stock"),
        }

    @staticmethod
    def _sector_tooltip_details(universe: str, sector: str | None) -> list[str]:
        if not sector or sector == "— all sectors —":
            return ["Select a sector to see stock and industry details."]

        counts = get_sector_industry_counts(universe, sector)
        total = get_universe_sector_stock_count(universe, sector)
        undef_count = counts.get("undefined", 0)
        assigned = total - undef_count
        details = [
            f"Total stocks: {total}",
            f"Classified: {assigned}",
        ]
        if undef_count:
            details.append(f"Unclassified: {undef_count}")
        for industry, count in counts.items():
            label = "Unclassified" if industry == "undefined" else industry
            details.append(f"{label}: {count}")
        return details

    def render(
        self,
        universe: str,
        sector: str | None = None,
        industry: str | None = None,
        stock: str | None = None,
    ) -> None:
        """Render the appropriate sector/industry/stocks view based on selected scope.
        
        Args:
            universe: Selected market universe (e.g., 'S&P 500')
            sector: Optional selected sector name; if None, renders sector grid
            industry: Optional selected industry; only valid if sector is also set
        """
        if sector and industry:
            render_industry_stock_page(sector, industry, stock=stock)
        elif sector:
            render_industry_dashboard(sector)
        else:
            if get_universe_sectors(universe):
                render_sector_grid(universe)
            else:
                render_industry_dashboard(None)
