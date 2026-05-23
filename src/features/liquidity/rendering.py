"""Backward-compatible aliases for renamed suggestions rendering."""

from ..suggestions.rendering import (
    get_suggested_industries,
    get_suggested_industry_stocks,
    render_suggestions_view,
    suggestions_refresh_tickers,
)


def liquidity_refresh_tickers(universe: str, selected_sector: str | None, all_markets: bool = False) -> list[str]:
    _ = selected_sector
    _ = all_markets
    return suggestions_refresh_tickers(universe, "1y", 10, 20, 20, 1.10)


def render_liquidity_chessboard(universe: str, selected_sector: str | None) -> None:
    _ = selected_sector
    render_suggestions_view(universe, "1y", 10, 10, 20, 20, 1.10)

__all__ = [
    "get_suggested_industries",
    "get_suggested_industry_stocks",
    "suggestions_refresh_tickers",
    "render_suggestions_view",
    "liquidity_refresh_tickers",
    "render_liquidity_chessboard",
]
