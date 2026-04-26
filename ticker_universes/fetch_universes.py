"""Fetch S&P 500 and S&P 100 lists from Wikipedia, write to CSV."""
import pandas as pd
import os
from io import StringIO
from curl_cffi import requests as curl_requests

OUT_DIR = os.path.dirname(__file__) or "."

def fetch_html(url):
    r = curl_requests.get(url, impersonate="chrome")
    r.raise_for_status()
    return r.text

# ---------- S&P 500 ----------
print("Fetching S&P 500 from Wikipedia...")
html = fetch_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
tables = pd.read_html(StringIO(html))
sp500 = tables[0]
# Wikipedia columns: Symbol, Security, GICS Sector, GICS Sub-Industry, ...
sp500 = sp500.rename(columns={
    "Symbol": "Ticker",
    "Security": "Name",
    "GICS Sector": "Sector",
    "GICS Sub-Industry": "Industry",
})
sp500 = sp500[["Ticker", "Name", "Sector", "Industry"]].copy()
sp500["Ticker"] = sp500["Ticker"].str.strip()
sp500 = sp500.sort_values("Ticker").reset_index(drop=True)
sp500.to_csv(os.path.join(OUT_DIR, "sp500.csv"), index=False)
print(f"  Wrote {len(sp500)} rows to sp500.csv")

# ---------- S&P 100 ----------
print("Fetching S&P 100 from Wikipedia...")
html100 = fetch_html("https://en.wikipedia.org/wiki/S%26P_100")
tables100 = pd.read_html(StringIO(html100))
# The constituent table has columns: Symbol, Name, Sector
sp100_wiki = tables100[2]  # Usually the 3rd table
# Try to find the right table
for i, t in enumerate(tables100):
    cols_lower = [str(c).lower() for c in t.columns]
    if "symbol" in cols_lower:
        sp100_wiki = t
        print(f"  Found S&P 100 table at index {i} with columns {list(t.columns)}")
        break

sp100_wiki = sp100_wiki.rename(columns={
    "Symbol": "Ticker",
    "Name": "Name",
    "Sector": "Sector",
})
sp100_wiki["Ticker"] = sp100_wiki["Ticker"].str.strip()
# Merge with sp500 to get Industry
sp100_merged = sp100_wiki[["Ticker", "Name"]].merge(
    sp500[["Ticker", "Sector", "Industry"]], on="Ticker", how="left"
)
# For any missing, keep Wikipedia sector
if "Sector" in sp100_wiki.columns:
    mask = sp100_merged["Sector"].isna()
    sp100_merged.loc[mask, "Sector"] = sp100_wiki.loc[mask, "Sector"].values if mask.any() else None
sp100_merged["Sector"] = sp100_merged["Sector"].fillna("undefined").str.strip().replace("", "undefined")
sp100_merged["Industry"] = sp100_merged["Industry"].fillna("undefined").str.strip().replace("", "undefined")
sp100_merged = sp100_merged[["Ticker", "Name", "Sector", "Industry"]].sort_values("Ticker").reset_index(drop=True)
sp100_merged.to_csv(os.path.join(OUT_DIR, "sp100.csv"), index=False)
print(f"  Wrote {len(sp100_merged)} rows to sp100.csv")

# ---------- Russell 2000 ----------
print("Fetching Russell 2000 (IWM holdings) from iShares...")
iwm_url = "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/1467271812596.ajax?fileType=csv&fileName=IWM_holdings&dataType=fund"
iwm_resp = curl_requests.get(iwm_url, impersonate="chrome")
iwm_resp.raise_for_status()
# iShares CSV has metadata rows before the actual header
lines = iwm_resp.text.split("\n")
header_idx = None
for i, line in enumerate(lines):
    if line.startswith("Ticker,"):
        header_idx = i
        break
assert header_idx is not None, "Could not find header row in IWM CSV"
iwm_csv = "\n".join(lines[header_idx:])
iwm = pd.read_csv(StringIO(iwm_csv))
# Keep only equity rows with a valid ticker
iwm = iwm[iwm["Asset Class"] == "Equity"].copy()
iwm = iwm[iwm["Ticker"].notna() & (iwm["Ticker"] != "-")].copy()
iwm["Ticker"] = iwm["Ticker"].str.strip().str.strip('"')
iwm["Name"] = iwm["Name"].str.strip().str.strip('"')
iwm["Sector"] = iwm["Sector"].str.strip().str.strip('"')

# Load financedatabase for industry mapping
print("  Loading financedatabase for industry lookup...")
import financedatabase as fd
eq = fd.Equities()
fdb = eq.select()
fdb = fdb.reset_index().rename(columns={"symbol": "Ticker", "industry": "FDB_Industry", "sector": "FDB_Sector"})
fdb = fdb[["Ticker", "FDB_Sector", "FDB_Industry"]].drop_duplicates(subset="Ticker")

# Merge IWM tickers with financedatabase industries
russell = iwm[["Ticker", "Name", "Sector"]].merge(fdb[["Ticker", "FDB_Industry"]], on="Ticker", how="left")
russell = russell.rename(columns={"FDB_Industry": "Industry"})
russell["Sector"] = russell["Sector"].fillna("undefined").str.strip().replace("", "undefined")
russell["Industry"] = russell["Industry"].fillna("undefined").str.strip().replace("", "undefined")
russell = russell[["Ticker", "Name", "Sector", "Industry"]].sort_values("Ticker").reset_index(drop=True)
russell.to_csv(os.path.join(OUT_DIR, "russell2000.csv"), index=False)
print(f"  Wrote {len(russell)} rows to russell2000.csv")
print(f"  Industry coverage: {russell['Industry'].notna().sum()}/{len(russell)} ({100*russell['Industry'].notna().mean():.1f}%)")

# ---------- STOXX Europe 600 ----------
print("Fetching STOXX Europe 600 from Wikipedia...")
html_stoxx = fetch_html("https://en.wikipedia.org/wiki/STOXX_Europe_600")
tables_stoxx = pd.read_html(StringIO(html_stoxx))
# Find the constituents table (has Ticker, Company, ICB Sector, Country columns)
stoxx = None
for i, t in enumerate(tables_stoxx):
    cols_lower = [str(c).lower() for c in t.columns]
    if "ticker" in cols_lower and "company" in cols_lower:
        stoxx = t
        print(f"  Found STOXX 600 table at index {i} with columns {list(t.columns)}")
        break
assert stoxx is not None, "Could not find STOXX 600 constituents table"
stoxx = stoxx.rename(columns={
    "Company": "Name",
    "ICB Sector": "Sector",
    "Country": "Country",
})
stoxx["Ticker"] = stoxx["Ticker"].str.strip()
# ICB Sector is the broad sector; use it as both Sector and Industry (ICB doesn't split further on Wikipedia)
stoxx["Industry"] = stoxx["Sector"]
stoxx = stoxx[["Ticker", "Name", "Sector", "Industry"]].sort_values("Ticker").reset_index(drop=True)
stoxx.to_csv(os.path.join(OUT_DIR, "stoxx600.csv"), index=False)
print(f"  Wrote {len(stoxx)} rows to stoxx600.csv")

# ---------- Hang Seng Index ----------
print("Fetching Hang Seng Index from Wikipedia...")
html_hsi = fetch_html("https://en.wikipedia.org/wiki/Hang_Seng_Index")
tables_hsi = pd.read_html(StringIO(html_hsi))
hsi = None
for i, t in enumerate(tables_hsi):
    cols_lower = [str(c).lower() for c in t.columns]
    if "ticker" in cols_lower and "name" in cols_lower:
        hsi = t
        print(f"  Found Hang Seng table at index {i} with columns {list(t.columns)}")
        break
assert hsi is not None, "Could not find Hang Seng constituents table"

def clean_hk_ticker(t):
    num = str(t).replace("SEHK:", "").strip()
    return f"{int(num):04d}.HK"

hsi["Ticker"] = hsi["Ticker"].apply(clean_hk_ticker)
hsi = hsi.rename(columns={"Sub-index": "Sector"})
hsi["Industry"] = hsi["Sector"]
hsi = hsi[["Ticker", "Name", "Sector", "Industry"]].sort_values("Ticker").reset_index(drop=True)
hsi.to_csv(os.path.join(OUT_DIR, "hangseng.csv"), index=False)
print(f"  Wrote {len(hsi)} rows to hangseng.csv")

# ---------- NASDAQ ----------
print("Fetching NASDAQ-listed equities from financedatabase...")
# financedatabase already loaded above; select exchange = NMS (NASDAQ Market System) / NGM / NCM
eq_all = eq.select()
eq_all = eq_all.reset_index().rename(columns={
    "symbol": "Ticker", "name": "Name",
    "sector": "Sector", "industry": "Industry", "exchange": "Exchange"
})
nasdaq_exchanges = {"NMS", "NGM", "NCM"}  # NASDAQ Global Select, Global Market, Capital Market
nasdaq = eq_all[eq_all["Exchange"].isin(nasdaq_exchanges)].copy()
nasdaq = nasdaq[nasdaq["Ticker"].notna() & (nasdaq["Ticker"].str.strip() != "")]
nasdaq = nasdaq[["Ticker", "Name", "Sector", "Industry"]].copy()
nasdaq["Ticker"] = nasdaq["Ticker"].str.strip()
nasdaq["Sector"] = nasdaq["Sector"].fillna("undefined").str.strip().replace("", "undefined")
nasdaq["Industry"] = nasdaq["Industry"].fillna("undefined").str.strip().replace("", "undefined")
nasdaq = nasdaq.sort_values("Ticker").reset_index(drop=True)
nasdaq.to_csv(os.path.join(OUT_DIR, "nasdaq.csv"), index=False)
print(f"  Wrote {len(nasdaq)} rows to nasdaq.csv")

# ---------- NYSE ----------
print("Fetching NYSE-listed equities from financedatabase...")
nyse_exchanges = {"NYQ", "NYSEArca", "NGM"}
nyse = eq_all[eq_all["Exchange"] == "NYQ"].copy()
nyse = nyse[nyse["Ticker"].notna() & (nyse["Ticker"].str.strip() != "")]
nyse = nyse[["Ticker", "Name", "Sector", "Industry"]].copy()
nyse["Ticker"] = nyse["Ticker"].str.strip()
nyse["Sector"] = nyse["Sector"].fillna("undefined").str.strip().replace("", "undefined")
nyse["Industry"] = nyse["Industry"].fillna("undefined").str.strip().replace("", "undefined")
nyse = nyse.sort_values("Ticker").reset_index(drop=True)
nyse.to_csv(os.path.join(OUT_DIR, "nyse.csv"), index=False)
print(f"  Wrote {len(nyse)} rows to nyse.csv")

# ---------- ASX 200 ----------
print("Fetching ASX 200 from Wikipedia...")
html_asx = fetch_html("https://en.wikipedia.org/wiki/S%26P/ASX_200")
tables_asx = pd.read_html(StringIO(html_asx))
asx = None
for t in tables_asx:
    cols = [str(c).lower() for c in t.columns]
    if "code" in cols and ("company" in cols or "name" in cols):
        asx = t
        break
assert asx is not None, "Could not find ASX 200 table"
asx = asx[["Code", "Company", "Sector"]].copy()
asx.columns = ["Ticker", "Name", "Sector"]
asx["Ticker"] = asx["Ticker"].astype(str).str.strip() + ".AX"
asx["Industry"] = asx["Sector"]
for col in ("Sector", "Industry"):
    asx[col] = asx[col].fillna("undefined").replace("", "undefined")
asx = asx[["Ticker", "Name", "Sector", "Industry"]].sort_values("Ticker").reset_index(drop=True)
asx.to_csv(os.path.join(OUT_DIR, "asx200.csv"), index=False)
print(f"  Wrote {len(asx)} rows to asx200.csv")

# ---------- Ibovespa (Brazil B3) ----------
print("Fetching Ibovespa constituents via yfinance (.SA suffix)...")
import yfinance as yf
IBOV_BASE = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "ABEV3", "WEGE3", "RENT3", "RDOR3",
    "BBAS3", "B3SA3", "SUZB3", "PRIO3", "CSAN3", "LREN3", "GGBR4", "CMIG4",
    "VIVT3", "BPAC11", "HAPV3", "SBSP3", "EGIE3", "TAEE11", "EQTL3", "CPLE6",
    "JBSS3", "BEEF3", "ARZZ3", "NTCO3", "MULT3", "ENGI11", "FLRY3", "QUAL3",
    "BBSE3", "IRBR3", "SULA11", "BRAP4", "USIM5", "CSNA3", "CYRE3", "EZTC3",
    "JHSF3", "MRVE3", "DIRR3", "GFSA3", "SAPR11", "TIMS3", "ALPA4", "MDIA3",
    "ELET3", "EMBR3",
]
ibov_rows = []
for base in IBOV_BASE:
    sym = f"{base}.SA"
    try:
        info = yf.Ticker(sym).get_info() or {}
        ibov_rows.append({
            "Ticker": sym,
            "Name": info.get("longName") or info.get("shortName") or sym,
            "Sector": info.get("sector") or "undefined",
            "Industry": info.get("industry") or "undefined",
        })
    except Exception:
        ibov_rows.append({"Ticker": sym, "Name": sym, "Sector": "undefined", "Industry": "undefined"})
ibov_df = pd.DataFrame(ibov_rows).sort_values("Ticker").reset_index(drop=True)
ibov_df.to_csv(os.path.join(OUT_DIR, "ibovespa.csv"), index=False)
print(f"  Wrote {len(ibov_df)} rows to ibovespa.csv")

# ---------- JSE Top 40 (South Africa) ----------
print("Fetching JSE Top 40 constituents via yfinance (.JO suffix)...")
JSE_BASE = [
    "ABG", "AGL", "AMS", "ANG", "APN", "BAW", "BHP", "BID", "BTI", "CFR",
    "CLS", "CPI", "DSY", "EXX", "FSR", "GFI", "GLN", "GRT", "HAR", "INL",
    "INP", "LHC", "MCG", "MNP", "MRP", "MTN", "NED", "NPN", "NPH", "OMU",
    "REM", "SHP", "SLM", "SPP", "SSL", "TFG", "VOD", "WHL", "SOL", "SNT",
]
jse_rows = []
for base in JSE_BASE:
    sym = f"{base}.JO"
    try:
        info = yf.Ticker(sym).get_info() or {}
        jse_rows.append({
            "Ticker": sym,
            "Name": info.get("longName") or info.get("shortName") or sym,
            "Sector": info.get("sector") or "undefined",
            "Industry": info.get("industry") or "undefined",
        })
    except Exception:
        jse_rows.append({"Ticker": sym, "Name": sym, "Sector": "undefined", "Industry": "undefined"})
jse_df = pd.DataFrame(jse_rows).sort_values("Ticker").reset_index(drop=True)
jse_df.to_csv(os.path.join(OUT_DIR, "jse_top40.csv"), index=False)
print(f"  Wrote {len(jse_df)} rows to jse_top40.csv")

print("Done!")
