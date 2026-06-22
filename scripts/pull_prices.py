"""
One-time pull of public commodity futures data for the FDE exercise.
Run this locally (requires internet access to Yahoo Finance, which this
sandbox does not have). Output: static CSVs in data/prices/, the
prototype reads from these files, not a live connection.

Usage:
    pip install yfinance --break-system-packages
    python pull_prices.py
"""

import yfinance as yf
import pandas as pd

TICKERS = {
    "cocoa": "CC=F",
    "sugar": "SB=F",
}

# Dairy has no liquid, clean Yahoo Finance ticker. CME Class III milk
# futures (DC=F) exist but coverage/liquidity is thin and inconsistent.
# Try it, but DO NOT fabricate clean data if it fails or is sparse, an
# incomplete dairy series is realistic messiness, document the gap rather
# than smoothing over it.
DAIRY_TICKER = "DC=F"

PERIOD = "24mo"
INTERVAL = "1wk"  # weekly granularity is enough for a benchmark series

def pull(ticker, label):
    df = yf.download(ticker, period=PERIOD, interval=INTERVAL)
    if df.empty:
        print(f"WARNING: no data returned for {label} ({ticker})")
        return None
    df = df[["Close"]].reset_index()
    df.columns = ["date", "price"]
    df["commodity"] = label
    return df

def main():
    frames = []
    for label, ticker in TICKERS.items():
        df = pull(ticker, label)
        if df is not None:
            frames.append(df)
            df.to_csv(f"data/prices/{label}_24mo.csv", index=False)
            print(f"Saved data/prices/{label}_24mo.csv ({len(df)} rows)")

    dairy_df = pull(DAIRY_TICKER, "dairy")
    if dairy_df is not None and len(dairy_df) > 10:
        dairy_df.to_csv("data/prices/dairy_24mo.csv", index=False)
        print(f"Saved data/prices/dairy_24mo.csv ({len(dairy_df)} rows)")
    else:
        print(
            "Dairy data is sparse or unavailable via Yahoo Finance. "
            "Do not fake this series. Document it as a real data gap in "
            "the prototype (e.g. 'limited public benchmark availability "
            "for dairy, category priced via direct supplier negotiation "
            "more than index tracking') instead of generating fake rows."
        )

    if frames:
        combined = pd.concat(frames, ignore_index=True)
        combined.to_csv("data/prices/combined_24mo.csv", index=False)
        print(f"Saved data/prices/combined_24mo.csv ({len(combined)} rows)")

if __name__ == "__main__":
    main()
