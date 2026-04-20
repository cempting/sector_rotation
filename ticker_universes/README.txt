Stock universe CSV files for the Sector Rotation Screener.

Each CSV must have the header: Ticker,Name,Sector,Industry

Built-in universes:
- sp100.csv       S&P 100 (from Wikipedia)
- sp500.csv       S&P 500 (from Wikipedia)
- russell2000.csv Russell 2000 (from iShares IWM + financedatabase)
- stoxx600.csv    STOXX Europe 600 (from Wikipedia)
- hangseng.csv    Hang Seng Index (from Wikipedia)

To regenerate from online sources:
    python fetch_universes.py

Custom universes:
  Drop any CSV with Ticker,Name,Sector,Industry columns here.
  It will appear in the dashboard sidebar dropdown automatically.

Example:
    Ticker,Name,Sector,Industry
    AAPL,Apple Inc.,Information Technology,Technology Hardware
    MSFT,Microsoft,Information Technology,Systems Software