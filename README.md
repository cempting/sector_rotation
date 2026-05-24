# Sector Rotation Screener

Streamlit app for market rotation exploration across stock universes, with feature-based navigation for:

- Sector/Industry/Stock drill-down browsing
- Search across all universes
- Favorites management (export/import JSON)
- Trend and volume suggestions

## Quick start

1. Create and activate a virtual environment:

```bash
python -m venv env
source env/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
streamlit run main.py
```

4. Run tests:

```bash
pytest
```

## How to use the app

The app uses a sticky top navigation bar. Choose a feature first, then use feature-specific controls.

### Sector / Industry / Stocks

- Choose a universe.
- Drill down by Sector, then Industry, then optional Stock.
- Use the refresh button to clear cached data for the current scope and reload market data.

### Search

- Enter ticker, company name, sector, or industry in the search box.
- Results are grouped by universe.
- Refresh reloads the current search result tickers.

### Favorites

- View favorited tickers grouped by universe.
- Export favorites as JSON.
- Import JSON and either merge or replace existing favorites.

### Suggestions

- Select a universe.
- Discover industries and stocks with trend + volume filters.
- Refresh clears cached suggestion computations and reloads relevant tickers.

### Data retry behavior

- If a ticker repeatedly returns no data (for example delisted or unavailable symbols), the app marks it as temporarily unavailable.
- Temporarily unavailable tickers are skipped for a cooldown window before trying again.
- This reduces repeated failed requests and keeps the app responsive.

## Stock universes

Universe files live in `ticker_universes/` and are auto-discovered.

- Required columns: `Ticker`, `Name`, `Sector`, `Industry`
- Custom CSVs with these columns are picked up automatically

Refresh built-in universe CSVs:

```bash
cd ticker_universes
python fetch_universes.py
```

## Architecture summary

- Entry point: `main.py`
- App shell: `src/dashboard.py`
- Feature routing: `src/features/__init__.py` (`FeatureRegistry`)
- Feature contract: `src/core/ui/interface.py` (`FeatureView`)
- Data layer: `src/core/data/`
- Analytics layer: `src/core/analytics/`

Detailed design documentation is available in `docs/app-design.md`.

## Project structure

```text
sector_rotation/
|- main.py
|- src/
|  |- dashboard.py
|  |- core/
|  |  |- data/
|  |  |- analytics/
|  |  |- ui/
|  |- features/
|  |  |- sector_industry_stocks/
|  |  |- search/
|  |  |- favorites/
|  |  |- suggestions/
|  |  |- liquidity/
|  |- charts.py
|  |- constants.py
|- ticker_universes/
|- data_cache/
|- tests/
```

## Extending the app

### Add a feature

1. Create `src/features/<feature_name>/`.
2. Implement a class inheriting `FeatureView`.
3. Register it in `src/features/__init__.py` via `FeatureRegistry.register_feature(...)`.
4. Add route mapping in `src/dashboard.py`.
5. Add/adjust tests in `tests/features/` and `tests/test_feature_routing.py`.

### Add a market/universe

1. Add CSV under `ticker_universes/`.
2. Register it in `src/constants.py` (`BUILTIN_UNIVERSE_FILES`).
3. Map the universe to a market key (`UNIVERSE_MARKET`).
4. Add sector proxy mapping in `MARKET_SECTOR_CONFIG`.
5. Validate with targeted tests and manual smoke-check in the UI.
 