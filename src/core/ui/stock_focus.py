from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TypeVar

import streamlit as st


DETAILS_FOCUS_UNIVERSE_KEY = "details_focus_universe"
DETAILS_FOCUS_TICKER_KEY = "details_focus_ticker"
DETAILS_OPENING_TICKER_KEY = "details_opening_ticker"

_ItemT = TypeVar("_ItemT")


@dataclass(frozen=True)
class DedicatedStockFocus:
    universe: str | None
    ticker: str | None

    @property
    def active(self) -> bool:
        return bool(self.universe and self.ticker)


@dataclass(frozen=True)
class GroupedStockFocusContext:
    render_groups: dict[str, list[object]]
    focus: DedicatedStockFocus
    narrowed: bool
    caption: str | None


def get_dedicated_stock_focus() -> DedicatedStockFocus:
    return DedicatedStockFocus(
        universe=st.session_state.get(DETAILS_FOCUS_UNIVERSE_KEY),
        ticker=st.session_state.get(DETAILS_FOCUS_TICKER_KEY),
    )


def open_dedicated_stock_view(universe: str, ticker: str) -> None:
    st.session_state[DETAILS_FOCUS_UNIVERSE_KEY] = universe
    st.session_state[DETAILS_FOCUS_TICKER_KEY] = ticker
    st.session_state[DETAILS_OPENING_TICKER_KEY] = ticker


def clear_dedicated_stock_view() -> None:
    st.session_state.pop(DETAILS_FOCUS_UNIVERSE_KEY, None)
    st.session_state.pop(DETAILS_FOCUS_TICKER_KEY, None)
    st.session_state.pop(DETAILS_OPENING_TICKER_KEY, None)


def pop_opening_ticker() -> str | None:
    return st.session_state.pop(DETAILS_OPENING_TICKER_KEY, None)


def is_dedicated_focus_for_ticker(selected_universe: str, tickers: Sequence[str]) -> str | None:
    focus = get_dedicated_stock_focus()
    if focus.universe != selected_universe or not focus.ticker:
        return None
    if focus.ticker not in tickers:
        return None
    return focus.ticker


def filter_grouped_for_dedicated_focus(
    grouped: Mapping[str, Sequence[_ItemT]],
    ticker_getter: Callable[[_ItemT], str],
) -> tuple[dict[str, list[_ItemT]], DedicatedStockFocus]:
    focus = get_dedicated_stock_focus()
    if not focus.active or focus.universe not in grouped:
        return {universe: list(items) for universe, items in grouped.items()}, focus

    focused_items = [item for item in grouped[focus.universe] if ticker_getter(item) == focus.ticker]
    if not focused_items:
        return {universe: list(items) for universe, items in grouped.items()}, focus

    return {focus.universe: list(grouped[focus.universe])}, focus


def prepare_grouped_stock_focus(
    grouped: Mapping[str, Sequence[_ItemT]],
    ticker_getter: Callable[[_ItemT], str],
    caption_prefix: str,
) -> GroupedStockFocusContext:
    render_groups, focus = filter_grouped_for_dedicated_focus(grouped, ticker_getter)
    narrowed = set(render_groups.keys()) != set(grouped.keys())
    caption = None
    if narrowed and focus.active:
        caption = f"{caption_prefix} · {focus.ticker} · {focus.universe}"

    return GroupedStockFocusContext(
        render_groups={universe: list(items) for universe, items in render_groups.items()},
        focus=focus,
        narrowed=narrowed,
        caption=caption,
    )