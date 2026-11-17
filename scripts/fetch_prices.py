"""Cache daily closing prices in the database.

Run:  python -m scripts.fetch_prices            # stocks someone holds or watches
      python -m scripts.fetch_prices --all      # every active stock
      python -m scripts.fetch_prices --period 5y

Why cache at all: drawing a chart of portfolio value over a year would
otherwise mean hundreds of API calls every time the page loads. Fetch
once a day, read locally forever after.

Safe to re-run. The UNIQUE constraint on (stock_id, price_date) means a
second run updates existing days instead of duplicating them.
"""

from __future__ import annotations

import argparse

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.price_history import PriceHistory
from app.models.stock import Stock
from app.models.transaction import Transaction
from app.models.watchlist import WatchlistItem
from app.services.market_data import market_data


def stocks_in_use(session: Session) -> list[Stock]:
    """Stocks any user holds or watches.

    Fetching prices for every listed company would be thousands of
    requests for data nobody looks at.
    """
    held = select(Transaction.stock_id).distinct()
    watched = select(WatchlistItem.stock_id).distinct()

    statement = (
        select(Stock)
        .where(Stock.is_active.is_(True))
        .where(or_(Stock.id.in_(held), Stock.id.in_(watched)))
        .order_by(Stock.symbol)
    )
    return list(session.execute(statement).scalars())


def all_active_stocks(session: Session) -> list[Stock]:
    return list(
        session.execute(
            select(Stock).where(Stock.is_active.is_(True)).order_by(Stock.symbol)
        ).scalars()
    )


def store_bars(session: Session, stock: Stock, period: str) -> tuple[int, int]:
    """Fetch and upsert one stock's history. Returns (inserted, updated)."""
    bars = market_data.get_history(stock.yahoo_symbol or f"{stock.symbol}.NS", period)
    if not bars:
        return 0, 0

    existing = {
        row.price_date: row
        for row in session.execute(
            select(PriceHistory).where(PriceHistory.stock_id == stock.id)
        ).scalars()
    }

    inserted = 0
    updated = 0

    for bar in bars:
        row = existing.get(bar.price_date)
        if row is None:
            session.add(
                PriceHistory(
                    stock_id=stock.id,
                    price_date=bar.price_date,
                    open_price=bar.open_price,
                    high_price=bar.high_price,
                    low_price=bar.low_price,
                    close_price=bar.close_price,
                    volume=bar.volume,
                )
            )
            inserted += 1
        else:
            # Prices do get revised, and the most recent day is partial
            # until the market closes, so overwriting is correct.
            row.open_price = bar.open_price
            row.high_price = bar.high_price
            row.low_price = bar.low_price
            row.close_price = bar.close_price
            row.volume = bar.volume
            updated += 1

    return inserted, updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="every active stock")
    parser.add_argument("--period", default="1y", help="yfinance period, e.g. 1y, 5y, max")
    args = parser.parse_args()

    with SessionLocal() as session:
        stocks = all_active_stocks(session) if args.all else stocks_in_use(session)

        if not stocks:
            print("No stocks to fetch. Record a transaction or add a watchlist item.")
            return

        print(f"Fetching {args.period} of prices for {len(stocks)} stock(s)...")
        total_inserted = 0
        total_updated = 0
        failed: list[str] = []

        for stock in stocks:
            inserted, updated = store_bars(session, stock, args.period)
            if inserted == 0 and updated == 0:
                failed.append(stock.symbol)
            else:
                print(f"  {stock.symbol:12} +{inserted} new, {updated} updated")
            total_inserted += inserted
            total_updated += updated

            # Commit per stock, so an upstream failure halfway through
            # does not throw away the work already done.
            session.commit()

    print(f"\nDone. {total_inserted} rows inserted, {total_updated} updated.")
    if failed:
        print(f"No data returned for: {', '.join(failed)}")


if __name__ == "__main__":
    main()
