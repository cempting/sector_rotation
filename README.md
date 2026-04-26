# Sector Rotation Screener

A Streamlit dashboard for visualizing market sector/industry rotations and screening equities. Supports multiple stock universes (S&P 100, S&P 500, Russell 2000, STOXX Europe 600, Hang Seng) with drill-down from sector → industry → individual stocks.

## Setup

1. Create and activate a Python virtual environment:

        python -m venv env
        source env/bin/activate    # Linux/Mac
        # env\Scripts\activate     # Windows

2. Install dependencies:

        pip install -r requirements.txt

## Run the dashboard

    streamlit run main.py

## Run tests

    pytest

## Project structure

    sector_rotation/
    ├── main.py                  # Streamlit entry point
    ├── src/
    │   ├── dashboard.py         # Main app layout and sidebar
    │   ├── renderers.py         # Sector/industry/stock card rendering
    │   ├── data.py              # Data fetchers (yfinance, financedatabase)
    │   ├── cache.py             # Ticker cache (load/save/background update)
    │   ├── universe.py          # Universe CSV loader (sectors, industries, tickers)
    │   ├── charts.py            # Chart rendering helpers
    │   └── constants.py         # Sector ETF map, layout constants
    ├── ticker_universes/        # Stock universe CSV files
    │   ├── fetch_universes.py   # Script to regenerate CSVs from online sources
    │   ├── sp100.csv
    │   ├── sp500.csv
    │   ├── russell2000.csv
    │   ├── stoxx600.csv
    │   └── hangseng.csv
    ├── data_cache/              # Local ticker data cache
    └── tests/

## Stock universes

The sidebar provides a dropdown to select a stock universe. Each universe is a CSV in `ticker_universes/` with columns: `Ticker, Name, Sector, Industry`. Selecting a universe drives the Sector and Industry dropdowns.

**Built-in universes:**

| Universe          | Source                              | Stocks |
|-------------------|-------------------------------------|--------|
| S&P 100           | Wikipedia                           | ~101   |
| S&P 500           | Wikipedia                           | ~503   |
| Russell 2000      | iShares IWM + financedatabase       | ~1,933 |
| NASDAQ            | financedatabase (NMS/NGM/NCM)       | ~7,875 |
| NYSE              | financedatabase (NYQ)               | ~3,543 |
| STOXX Europe 600  | Wikipedia                           | ~534   |
| Hang Seng         | Wikipedia                           | ~85    |

To refresh the CSVs from online sources:

    cd ticker_universes && python fetch_universes.py

**Custom universes:** Drop any CSV with `Ticker,Name,Sector,Industry` columns into `ticker_universes/` and it will appear in the sidebar dropdown automatically.
 