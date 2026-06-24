"""
utils/data_fetcher.py

Fetches live market reference data: FX rates, commodity spot prices, and
lending rates. Called once at app startup and cached in st.session_state.

All internal functions are fail-safe — exceptions are caught, logged to
stderr, and an empty DataFrame with correct columns is returned so the app
never crashes due to a failed external fetch.
"""

import sys
from datetime import date
from typing import Optional

import pandas as pd
import requests
import yfinance as yf


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_reference_data() -> dict:
    """
    Returns:
        {
          "fx_rates":             DataFrame  — latest close per currency pair
          "fx_trends":            DataFrame  — 30-day daily series per currency pair
          "commodity_benchmarks": DataFrame  — live spot prices
          "lending_rates":        DataFrame  — BOI prime, SOFR, EURIBOR
        }
    """
    fx_df = _fetch_fx_rates()
    return {
        "fx_rates":             fx_df,
        "fx_trends":            _fetch_fx_trends(),
        "commodity_benchmarks": _fetch_commodity_benchmarks(fx_df),
        "lending_rates":        _fetch_lending_rates(),
    }


# ── FX Rates ───────────────────────────────────────────────────────────────────

_FX_COLS = ["currency_pair", "rate", "as_of_date", "source"]

_FX_TICKERS = {
    "EURILS=X": "EUR/ILS",
    "USDILS=X": "USD/ILS",
    "PLNILS=X": "PLN/ILS",
    "GBPILS=X": "GBP/ILS",
}


def _fetch_fx_rates() -> pd.DataFrame:
    try:
        rows = []
        for ticker, label in _FX_TICKERS.items():
            try:
                df = yf.download(ticker, period="2d", auto_adjust=True, progress=False)
                if df.empty:
                    continue
                close = df["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                close = close.dropna()
                if close.empty:
                    continue
                rows.append({
                    "currency_pair": label,
                    "rate": round(float(close.iloc[-1]), 4),
                    "as_of_date": close.index[-1].date().isoformat(),
                    "source": "Yahoo Finance",
                })
            except Exception as e:
                print(f"[data_fetcher] FX {ticker} failed: {e}", file=sys.stderr)

        return pd.DataFrame(rows, columns=_FX_COLS) if rows else pd.DataFrame(columns=_FX_COLS)
    except Exception as e:
        print(f"[data_fetcher] _fetch_fx_rates failed: {e}", file=sys.stderr)
        return pd.DataFrame(columns=_FX_COLS)


# ── FX 30-day Trends ──────────────────────────────────────────────────────────

_FX_TRENDS_COLS = ["currency_pair", "date", "rate"]


def _fetch_fx_trends() -> pd.DataFrame:
    """30-day daily FX series for all tracked pairs. Used for trend charts."""
    try:
        frames = []
        for ticker, label in _FX_TICKERS.items():
            try:
                df = yf.download(ticker, period="1mo", auto_adjust=True, progress=False)
                if df.empty:
                    continue
                close = df["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                close = close.dropna().reset_index()
                close.columns = ["date", "rate"]
                close["currency_pair"] = label
                close["date"] = close["date"].dt.date.astype(str)
                close["rate"] = close["rate"].round(4)
                frames.append(close[_FX_TRENDS_COLS])
            except Exception as e:
                print(f"[data_fetcher] FX trend {ticker} failed: {e}", file=sys.stderr)
        if frames:
            return pd.concat(frames, ignore_index=True)
        return pd.DataFrame(columns=_FX_TRENDS_COLS)
    except Exception as e:
        print(f"[data_fetcher] _fetch_fx_trends failed: {e}", file=sys.stderr)
        return pd.DataFrame(columns=_FX_TRENDS_COLS)


# ── Commodity Benchmarks ───────────────────────────────────────────────────────

_COMMODITY_COLS = ["commodity", "ticker", "unit", "price_usd", "price_ils", "as_of_date", "source"]

_COMMODITY_TICKERS = {
    "CC=F": {
        "commodity": "Cocoa",
        "unit": "USD/metric ton",
        "source": "Yahoo Finance - ICE Futures",
    },
    "SB=F": {
        "commodity": "Sugar (No. 11)",
        "unit": "¢/lb",          # ICE No.11 is quoted in US cents per pound
        "source": "Yahoo Finance - ICE Futures",
    },
    "DC=F": {
        "commodity": "Dairy (Class III Milk)",
        "unit": "USD/hundredweight",
        "source": "Yahoo Finance - CME Futures",
    },
}


def _fetch_commodity_benchmarks(fx_df: pd.DataFrame) -> pd.DataFrame:
    try:
        usdils: Optional[float] = None
        if not fx_df.empty:
            row = fx_df[fx_df["currency_pair"] == "USD/ILS"]
            if not row.empty:
                usdils = float(row.iloc[0]["rate"])

        rows = []
        for ticker, meta in _COMMODITY_TICKERS.items():
            try:
                df = yf.download(ticker, period="2d", auto_adjust=True, progress=False)
                if df.empty:
                    continue
                close = df["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                close = close.dropna()
                if close.empty:
                    continue
                price_raw = round(float(close.iloc[-1]), 4)
                # Sugar is in ¢/lb; divide by 100 to get USD before ILS conversion
                usd_for_conversion = price_raw / 100 if ticker == "SB=F" else price_raw
                price_ils = round(usd_for_conversion * usdils, 4) if usdils else None
                rows.append({
                    "commodity": meta["commodity"],
                    "ticker": ticker,
                    "unit": meta["unit"],
                    "price_usd": price_raw,
                    "price_ils": price_ils,
                    "as_of_date": close.index[-1].date().isoformat(),
                    "source": meta["source"],
                })
            except Exception as e:
                print(f"[data_fetcher] Commodity {ticker} failed: {e}", file=sys.stderr)

        return pd.DataFrame(rows, columns=_COMMODITY_COLS) if rows else pd.DataFrame(columns=_COMMODITY_COLS)
    except Exception as e:
        print(f"[data_fetcher] _fetch_commodity_benchmarks failed: {e}", file=sys.stderr)
        return pd.DataFrame(columns=_COMMODITY_COLS)


# ── Lending Rates ──────────────────────────────────────────────────────────────

_LENDING_COLS = ["rate_type", "currency", "rate_pct", "as_of_date", "source", "notes"]


def _fetch_lending_rates() -> pd.DataFrame:
    rows = []
    today = date.today().isoformat()

    # ── Bank of Israel prime rate (ILS) ───────────────────────────────────────
    try:
        resp = requests.get(
            "https://edge.boi.gov.il/FusionEdgeServer/sdmx/v2/data/dataflow/"
            "BOI.STATISTICS/DP.M/1.0/INTHIST_PRIME?lastNObservations=1&format=json",
            timeout=5,
        )
        resp.raise_for_status()
        payload = resp.json()
        series = list(payload["data"]["dataSets"][0]["series"].values())[0]
        boi_rate = float(series["observations"]["0"][0])
        boi_source = "Bank of Israel API"
    except Exception as e:
        print(f"[data_fetcher] BOI rate failed: {e}", file=sys.stderr)
        boi_rate = 6.0
        boi_source = "fallback - BOI API unavailable"

    rows.append({
        "rate_type": "Prime Rate",
        "currency": "ILS",
        "rate_pct": boi_rate,
        "as_of_date": today,
        "source": boi_source,
        "notes": "ILS cost of capital - used to evaluate early payment discount attractiveness",
    })

    # ── SOFR (USD) ─────────────────────────────────────────────────────────────
    try:
        resp = requests.get(
            "https://markets.newyorkfed.org/api/rates/sofr/last/1.json",
            timeout=5,
        )
        resp.raise_for_status()
        sofr_rate = float(resp.json()["refRates"][0]["percentRate"])
        sofr_source = "NY Federal Reserve API"
    except Exception as e:
        print(f"[data_fetcher] SOFR rate failed: {e}", file=sys.stderr)
        sofr_rate = 5.3
        sofr_source = "fallback"

    rows.append({
        "rate_type": "SOFR",
        "currency": "USD",
        "rate_pct": sofr_rate,
        "as_of_date": today,
        "source": sofr_source,
        "notes": "USD benchmark - relevant for USD-denominated supplier contracts",
    })

    # ── EURIBOR 3-month (EUR) ──────────────────────────────────────────────────
    # EMMI publishes EURIBOR daily at euribor-rates.eu but requires registration for API access.
    rows.append({
        "rate_type": "EURIBOR 3M",
        "currency": "EUR",
        "rate_pct": 2.6,
        "as_of_date": today,
        "source": "hardcoded - replace with EMMI feed in production",
        "notes": "EUR benchmark - relevant for EUR-denominated supplier contracts",
    })

    return pd.DataFrame(rows, columns=_LENDING_COLS)
