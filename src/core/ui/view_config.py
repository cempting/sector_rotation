from typing import Literal, TypeAlias

StockRowSlot: TypeAlias = Literal["chart", "details", "macro", "recent"]
StockRowLayout: TypeAlias = list[tuple[StockRowSlot, float]]

BASE_CHART_WIDTH = 4.0
DEFAULT_STOCK_CHART_SIZE = (BASE_CHART_WIDTH, 2.8)
LIQUIDITY_STOCK_CHART_DEFAULT_HEIGHT = 4.0
REM_PER_MATPLOTLIB_INCH = 5

DEFAULT_BASIC_ROW_LAYOUT: StockRowLayout = [("chart", 1.0), ("details", 1.0)]
DEFAULT_LIQUIDITY_ROW_LAYOUT: StockRowLayout = [
    ("chart", 1.25),
    ("details", 1.0),
    ("macro", 1.0),
    ("recent", 1.0),
]

FAVORITES_CHART_HEIGHT = 5.0
FAVORITES_PANEL_MIN_HEIGHT_REM = FAVORITES_CHART_HEIGHT * REM_PER_MATPLOTLIB_INCH
FAVORITES_ROW_LAYOUT: StockRowLayout = [
    ("chart", 1.25),
    ("details", 1.0),
    ("macro", 1.0),
    ("recent", 1.0),
]

_ALLOWED_ROW_SLOTS: set[str] = {"chart", "details", "macro", "recent"}


def default_row_layout(show_liquidity_context: bool) -> StockRowLayout:
    return DEFAULT_LIQUIDITY_ROW_LAYOUT if show_liquidity_context else DEFAULT_BASIC_ROW_LAYOUT


def normalize_row_layout(
    row_layout: list[tuple[str, float]] | None,
    show_liquidity_context: bool,
) -> StockRowLayout:
    default_layout = default_row_layout(show_liquidity_context)
    if not row_layout:
        return default_layout

    normalized: StockRowLayout = []
    for slot, width in row_layout:
        if slot not in _ALLOWED_ROW_SLOTS:
            continue
        try:
            numeric_width = float(width)
        except (TypeError, ValueError):
            continue
        if numeric_width <= 0:
            continue
        normalized.append((slot, numeric_width))

    return normalized or default_layout
