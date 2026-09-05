"""One-off check: can we actually pull NSE prices from Yahoo Finance?

Run this BEFORE building anything that depends on market data.
If it fails, we switch data sources now rather than in three weeks.
"""

import yfinance as yf

TICKERS = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"]

print(f"yfinance version: {yf.__version__}\n")

for ticker in TICKERS:
    try:
        history = yf.Ticker(ticker).history(period="5d")
        if history.empty:
            print(f"{ticker:14} NO DATA RETURNED")
        else:
            last_close = float(history["Close"].iloc[-1])
            last_date = history.index[-1].date()
            print(f"{ticker:14} OK   last close Rs {last_close:,.2f} on {last_date}")
    except Exception as error:
        print(f"{ticker:14} FAILED  {type(error).__name__}: {error}")
