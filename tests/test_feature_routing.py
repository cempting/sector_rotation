"""Compatibility test entrypoint for legacy command paths.

This keeps `python -m pytest tests/test_feature_routing.py` working while the
canonical tests live under tests/features/sector_industry_stocks/.
"""

from pathlib import Path
import runpy

_globals = runpy.run_path(
    str(Path(__file__).parent / "features" / "sector_industry_stocks" / "test_routing.py")
)

for name, value in _globals.items():
    if name.startswith("test_"):
        globals()[name] = value
