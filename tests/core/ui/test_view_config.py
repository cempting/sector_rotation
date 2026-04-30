from sector_rotation.src.core.ui import view_config


def test_default_row_layout_switches_by_liquidity_flag():
    assert view_config.default_row_layout(False) == view_config.DEFAULT_BASIC_ROW_LAYOUT
    assert view_config.default_row_layout(True) == view_config.DEFAULT_LIQUIDITY_ROW_LAYOUT


def test_normalize_row_layout_returns_default_when_none():
    assert view_config.normalize_row_layout(None, False) == view_config.DEFAULT_BASIC_ROW_LAYOUT


def test_normalize_row_layout_filters_invalid_entries():
    row_layout = [
        ("chart", 1.25),
        ("details", "2.0"),
        ("bad_slot", 3.0),
        ("macro", -1.0),
        ("recent", 0),
        ("macro", 1.0),
    ]

    normalized = view_config.normalize_row_layout(row_layout, True)

    assert normalized == [("chart", 1.25), ("details", 2.0), ("macro", 1.0)]


def test_normalize_row_layout_falls_back_if_all_invalid():
    row_layout = [("bad", -1), ("also_bad", "x")]

    normalized = view_config.normalize_row_layout(row_layout, True)

    assert normalized == view_config.DEFAULT_LIQUIDITY_ROW_LAYOUT
