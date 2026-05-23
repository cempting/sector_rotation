from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import TypeVar

import streamlit as st

from .stock_focus import GroupedStockFocusContext, prepare_grouped_stock_focus


_ItemT = TypeVar("_ItemT")
GroupedItems = Mapping[str, Sequence[_ItemT]]
RenderStockCardsFn = Callable[..., None]
RenderGroupMetaFn = Callable[[str, list[_ItemT]], None]


def render_grouped_stock_sections(
    grouped: GroupedItems[_ItemT],
    ticker_getter: Callable[[_ItemT], str],
    render_stock_cards_fn: RenderStockCardsFn,
    focus_caption_prefix: str,
    render_group_meta_fn: RenderGroupMetaFn | None = None,
    *,
    empty_message: str = "",
    show_liquidity_context: bool | None = None,
    stocks_per_row: int | None = None,
    chart_height: float | None = None,
    row_layout: list[tuple[str, float]] | None = None,
) -> GroupedStockFocusContext:
    focus_context = prepare_grouped_stock_focus(grouped, ticker_getter, focus_caption_prefix)

    if focus_context.caption:
        st.caption(focus_context.caption)

    for universe_name, universe_items in focus_context.render_groups.items():
        st.markdown(f"**{universe_name}**")
        if render_group_meta_fn:
            render_group_meta_fn(universe_name, universe_items)

        tickers = list(dict.fromkeys(ticker_getter(item) for item in universe_items))
        cards_kwargs: dict[str, object] = {
            "tickers": tickers,
            "selected_universe": universe_name,
            "empty_message": empty_message,
        }
        if show_liquidity_context is not None:
            cards_kwargs["show_liquidity_context"] = show_liquidity_context
        if stocks_per_row is not None:
            cards_kwargs["stocks_per_row"] = stocks_per_row
        if chart_height is not None:
            cards_kwargs["chart_height"] = chart_height
        if row_layout is not None:
            cards_kwargs["row_layout"] = row_layout

        render_stock_cards_fn(**cards_kwargs)

    return focus_context