"""Load the stock list into the database.

Run:  python -m scripts.seed_stocks
      python -m scripts.seed_stocks path/to/EQUITY_L.csv

With no argument it loads the built-in list below: the large, liquid NSE
names, which is enough for search to be useful immediately and works with
no network at all.

With a CSV argument it loads NSE's published equity list (downloadable
from the NSE website as EQUITY_L.csv), which has every listed company.
The built-in list exists because relying on a scraped download for a
step this fundamental would mean the app cannot be set up on a bad day.

Safe to re-run: existing rows are updated, not duplicated.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.stock import Stock

# symbol, company name, sector
BUILT_IN: list[tuple[str, str, str]] = [
    ("RELIANCE", "Reliance Industries Ltd", "Energy"),
    ("TCS", "Tata Consultancy Services Ltd", "Information Technology"),
    ("HDFCBANK", "HDFC Bank Ltd", "Financial Services"),
    ("ICICIBANK", "ICICI Bank Ltd", "Financial Services"),
    ("INFY", "Infosys Ltd", "Information Technology"),
    ("HINDUNILVR", "Hindustan Unilever Ltd", "FMCG"),
    ("ITC", "ITC Ltd", "FMCG"),
    ("SBIN", "State Bank of India", "Financial Services"),
    ("BHARTIARTL", "Bharti Airtel Ltd", "Telecommunication"),
    ("KOTAKBANK", "Kotak Mahindra Bank Ltd", "Financial Services"),
    ("LT", "Larsen & Toubro Ltd", "Construction"),
    ("AXISBANK", "Axis Bank Ltd", "Financial Services"),
    ("ASIANPAINT", "Asian Paints Ltd", "Consumer Durables"),
    ("MARUTI", "Maruti Suzuki India Ltd", "Automobile"),
    ("BAJFINANCE", "Bajaj Finance Ltd", "Financial Services"),
    ("HCLTECH", "HCL Technologies Ltd", "Information Technology"),
    ("SUNPHARMA", "Sun Pharmaceutical Industries Ltd", "Pharmaceuticals"),
    ("TITAN", "Titan Company Ltd", "Consumer Durables"),
    ("ULTRACEMCO", "UltraTech Cement Ltd", "Construction Materials"),
    ("WIPRO", "Wipro Ltd", "Information Technology"),
    ("NESTLEIND", "Nestle India Ltd", "FMCG"),
    ("ONGC", "Oil & Natural Gas Corporation Ltd", "Energy"),
    ("NTPC", "NTPC Ltd", "Power"),
    ("POWERGRID", "Power Grid Corporation of India Ltd", "Power"),
    ("M&M", "Mahindra & Mahindra Ltd", "Automobile"),
    ("TATAMOTORS", "Tata Motors Ltd", "Automobile"),
    ("TATASTEEL", "Tata Steel Ltd", "Metals & Mining"),
    ("JSWSTEEL", "JSW Steel Ltd", "Metals & Mining"),
    ("ADANIENT", "Adani Enterprises Ltd", "Diversified"),
    ("ADANIPORTS", "Adani Ports and Special Economic Zone Ltd", "Infrastructure"),
    ("COALINDIA", "Coal India Ltd", "Energy"),
    ("BAJAJFINSV", "Bajaj Finserv Ltd", "Financial Services"),
    ("GRASIM", "Grasim Industries Ltd", "Construction Materials"),
    ("TECHM", "Tech Mahindra Ltd", "Information Technology"),
    ("INDUSINDBK", "IndusInd Bank Ltd", "Financial Services"),
    ("DRREDDY", "Dr. Reddy's Laboratories Ltd", "Pharmaceuticals"),
    ("CIPLA", "Cipla Ltd", "Pharmaceuticals"),
    ("DIVISLAB", "Divi's Laboratories Ltd", "Pharmaceuticals"),
    ("EICHERMOT", "Eicher Motors Ltd", "Automobile"),
    ("HEROMOTOCO", "Hero MotoCorp Ltd", "Automobile"),
    ("BAJAJ-AUTO", "Bajaj Auto Ltd", "Automobile"),
    ("BRITANNIA", "Britannia Industries Ltd", "FMCG"),
    ("TATACONSUM", "Tata Consumer Products Ltd", "FMCG"),
    ("HINDALCO", "Hindalco Industries Ltd", "Metals & Mining"),
    ("SHRIRAMFIN", "Shriram Finance Ltd", "Financial Services"),
    ("APOLLOHOSP", "Apollo Hospitals Enterprise Ltd", "Healthcare"),
    ("BPCL", "Bharat Petroleum Corporation Ltd", "Energy"),
    ("SBILIFE", "SBI Life Insurance Company Ltd", "Insurance"),
    ("HDFCLIFE", "HDFC Life Insurance Company Ltd", "Insurance"),
    ("LTIM", "LTIMindtree Ltd", "Information Technology"),
    ("TRENT", "Trent Ltd", "Retail"),
    ("DMART", "Avenue Supermarts Ltd", "Retail"),
    ("PIDILITIND", "Pidilite Industries Ltd", "Chemicals"),
    ("DABUR", "Dabur India Ltd", "FMCG"),
    ("GODREJCP", "Godrej Consumer Products Ltd", "FMCG"),
    ("HAVELLS", "Havells India Ltd", "Consumer Durables"),
    ("VEDL", "Vedanta Ltd", "Metals & Mining"),
    ("IOC", "Indian Oil Corporation Ltd", "Energy"),
    ("GAIL", "GAIL (India) Ltd", "Energy"),
    ("BEL", "Bharat Electronics Ltd", "Capital Goods"),
    ("HAL", "Hindustan Aeronautics Ltd", "Capital Goods"),
    ("PNB", "Punjab National Bank", "Financial Services"),
    ("BANKBARODA", "Bank of Baroda", "Financial Services"),
    ("CANBK", "Canara Bank", "Financial Services"),
    ("IRCTC", "Indian Railway Catering & Tourism Corporation Ltd", "Services"),
]


def rows_from_csv(path: Path) -> list[tuple[str, str, str]]:
    """Read NSE's EQUITY_L.csv.

    Its headers have leading spaces (" NAME OF COMPANY"), which is the
    kind of detail that breaks a naive importer, so keys are stripped.
    """
    rows: list[tuple[str, str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for raw in csv.DictReader(handle):
            record = {(key or "").strip(): (value or "").strip() for key, value in raw.items()}
            symbol = record.get("SYMBOL", "")
            name = record.get("NAME OF COMPANY", "")
            if symbol and name:
                rows.append((symbol, name, ""))
    return rows


def seed(rows: list[tuple[str, str, str]]) -> tuple[int, int]:
    """Insert or update each stock. Returns (created, updated)."""
    created = 0
    updated = 0

    with SessionLocal() as session:
        for symbol, name, sector in rows:
            existing = session.execute(
                select(Stock).where(Stock.symbol == symbol)
            ).scalar_one_or_none()

            if existing is None:
                session.add(
                    Stock(
                        symbol=symbol,
                        name=name,
                        exchange="NSE",
                        # Yahoo's own suffix for NSE listings. Derived once
                        # here so no other code has to know about it.
                        yahoo_symbol=f"{symbol}.NS",
                        sector=sector or None,
                        is_active=True,
                    )
                )
                created += 1
            else:
                existing.name = name
                if sector:
                    existing.sector = sector
                if not existing.yahoo_symbol:
                    existing.yahoo_symbol = f"{symbol}.NS"
                updated += 1

        # One commit for the whole batch: either the seed completes or the
        # table is untouched, rather than ending up half loaded.
        session.commit()

    return created, updated


def main() -> None:
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if not path.exists():
            raise SystemExit(f"No such file: {path}")
        rows = rows_from_csv(path)
        source = f"{path} ({len(rows)} rows)"
    else:
        rows = BUILT_IN
        source = f"built-in list ({len(rows)} stocks)"

    created, updated = seed(rows)
    print(f"Seeded from {source}")
    print(f"  created: {created}")
    print(f"  updated: {updated}")


if __name__ == "__main__":
    main()
