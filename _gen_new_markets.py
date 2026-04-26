"""One-shot generator for ASX 200 (already done), Ibovespa, and JSE Top 40 CSVs."""
import os
import pandas as pd
import yfinance as yf
from io import StringIO
from curl_cffi import requests as curl_requests

OUT = os.path.join(os.path.dirname(__file__), "ticker_universes")


def fetch_html(url):
    r = curl_requests.get(url, impersonate="chrome")
    r.raise_for_status()
    return r.text


# ── ASX 200 ──────────────────────────────────────────────────────────────────
def build_asx200():
    print("Fetching ASX 200 from Wikipedia...")
    html = fetch_html("https://en.wikipedia.org/wiki/S%26P/ASX_200")
    tables = pd.read_html(StringIO(html))
    asx = None
    for t in tables:
        cols = [str(c).lower() for c in t.columns]
        if "code" in cols and ("company" in cols or "name" in cols):
            asx = t
            break
    assert asx is not None
    asx = asx[["Code", "Company", "Sector"]].copy()
    asx.columns = ["Ticker", "Name", "Sector"]
    asx["Ticker"] = asx["Ticker"].astype(str).str.strip() + ".AX"
    asx["Industry"] = asx["Sector"]
    for col in ("Sector", "Industry"):
        asx[col] = asx[col].fillna("undefined").replace("", "undefined")
    asx = asx[["Ticker", "Name", "Sector", "Industry"]].sort_values("Ticker").reset_index(drop=True)
    asx.to_csv(os.path.join(OUT, "asx200.csv"), index=False)
    print(f"  Wrote {len(asx)} rows. Sectors: {sorted(asx['Sector'].unique())}")


# ── Ibovespa (Brazil B3) ─────────────────────────────────────────────────────
# Curated list of current Ibovespa constituents — yfinance uses .SA suffix.
IBOV_BASE = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "ABEV3", "WEGE3", "RENT3", "RDOR3",
    "BBAS3", "B3SA3", "SUZB3", "PRIO3", "CSAN3", "LREN3", "GGBR4", "CMIG4",
    "VIVT3", "BPAC11", "HAPV3", "SBSP3", "EGIE3", "TAEE11", "EQTL3", "CPLE6",
    "JBSS3", "BEEF3", "ARZZ3", "NTCO3", "MULT3", "ENGI11", "FLRY3", "QUAL3",
    "BBSE3", "IRBR3", "SULA11", "BRAP4", "USIM5", "CSNA3", "CYRE3", "EZTC3",
    "JHSF3", "MRVE3", "DIRR3", "GFSA3", "SAPR11", "TIMS3", "ALPA4", "MDIA3",
    "ELET3", "EMBR3",
]


def build_ibovespa():
    print(f"Fetching Ibovespa ({len(IBOV_BASE)} tickers)…")
    rows = []
    for base in IBOV_BASE:
        sym = f"{base}.SA"
        try:
            info = yf.Ticker(sym).get_info() or {}
            rows.append({
                "Ticker": sym,
                "Name": info.get("longName") or info.get("shortName") or sym,
                "Sector": info.get("sector") or "undefined",
                "Industry": info.get("industry") or "undefined",
            })
        except Exception:
            rows.append({"Ticker": sym, "Name": sym, "Sector": "undefined", "Industry": "undefined"})
    df = pd.DataFrame(rows).sort_values("Ticker").reset_index(drop=True)
    df.to_csv(os.path.join(OUT, "ibovespa.csv"), index=False)
    print(f"  Wrote {len(df)} rows. Sectors: {sorted(df['Sector'].unique())}")


# ── JSE Top 40 (South Africa) ────────────────────────────────────────────────
# Curated current JSE Top 40 constituents — Yahoo Finance uses .JO suffix.
JSE_BASE = [
    "ABG", "AGL", "AMS", "ANG", "APN", "BAW", "BHP", "BID", "BTI", "CFR",
    "CLS", "CPI", "DSY", "EXX", "FSR", "GFI", "GLN", "GRT", "HAR", "INL",
    "INP", "LHC", "MCG", "MNP", "MRP", "MTN", "NED", "NPN", "NPH", "OMU",
    "REM", "SHP", "SLM", "SPP", "SSL", "TFG", "VOD", "WHL", "SOL", "SNT",
]


def build_jse_top40():
    print(f"Fetching JSE Top 40 ({len(JSE_BASE)} tickers)…")
    rows = []
    for base in JSE_BASE:
        sym = f"{base}.JO"
        try:
            info = yf.Ticker(sym).get_info() or {}
            rows.append({
                "Ticker": sym,
                "Name": info.get("longName") or info.get("shortName") or sym,
                "Sector": info.get("sector") or "undefined",
                "Industry": info.get("industry") or "undefined",
            })
        except Exception:
            rows.append({"Ticker": sym, "Name": sym, "Sector": "undefined", "Industry": "undefined"})
    df = pd.DataFrame(rows).sort_values("Ticker").reset_index(drop=True)
    df.to_csv(os.path.join(OUT, "jse_top40.csv"), index=False)
    print(f"  Wrote {len(df)} rows. Sectors: {sorted(df['Sector'].unique())}")


if __name__ == "__main__":
    import sys
    targets = sys.argv[1:] or ["asx", "ibov", "jse"]
    if "asx" in targets:
        build_asx200()
    if "ibov" in targets:
        build_ibovespa()
    if "jse" in targets:
        build_jse_top40()
    print("Done.")
