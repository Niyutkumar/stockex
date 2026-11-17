"""Builds the dashboard view: database rows in, valued holdings out.

This is the seam between the pure position engine (app/services/portfolio.py,
which knows nothing about databases) and the web layer. Keeping the maths
out of here is what makes the maths testable.
"""

from __future__ import annotations

import bisect
from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.stock import Stock
from app.models.transaction import Transaction
from app.models.price_history import PriceHistory
from app.schemas.portfolio import (
    HistoryPoint,
    HoldingRead,
    PortfolioHistory,
    PortfolioSummary,
)
from app.services.market_data import MarketDataProvider
from app.services.portfolio import Trade, compute_position, value_position

ZERO = Decimal("0")


def _trades_by_stock(db: Session, user_id: int) -> dict[int, list[Trade]]:
    """Every trade this user has made, grouped by stock."""
    rows = db.execute(
        select(Transaction).where(Transaction.user_id == user_id)
    ).scalars()

    grouped: dict[int, list[Trade]] = defaultdict(list)
    for row in rows:
        grouped[row.stock_id].append(
            Trade(
                transaction_type=row.transaction_type,
                quantity=row.quantity,
                price=row.price,
                transaction_date=row.transaction_date,
                id=row.id,
            )
        )
    return grouped


def build_portfolio(
    db: Session,
    user_id: int,
    provider: MarketDataProvider,
) -> PortfolioSummary:
    """Compute the user's whole portfolio, priced at the market."""
    grouped = _trades_by_stock(db, user_id)

    if not grouped:
        return PortfolioSummary(
            total_cost=ZERO,
            total_value=ZERO,
            total_unrealized_pnl=ZERO,
            total_unrealized_pct=ZERO,
            total_realized_pnl=ZERO,
            holdings_count=0,
            priced_count=0,
            holdings=[],
        )

    stocks = {
        stock.id: stock
        for stock in db.execute(
            select(Stock).where(Stock.id.in_(grouped.keys()))
        ).scalars()
    }

    holdings: list[HoldingRead] = []
    total_cost = ZERO
    total_value = ZERO
    total_unrealized = ZERO
    # Realized profit counts from every stock, including ones sold out
    # completely and no longer held. Those are not listed as holdings but
    # the money was still made.
    total_realized = ZERO
    priced_count = 0

    for stock_id, trades in grouped.items():
        stock = stocks.get(stock_id)
        if stock is None:
            continue

        position = compute_position(trades)
        total_realized += position.realized_pnl

        if position.quantity <= ZERO:
            continue  # closed position: realized counted, nothing to list

        quote = provider.get_quote(stock.yahoo_symbol or f"{stock.symbol}.NS")

        if quote is None:
            # Price unavailable. Show the holding with what we know for
            # certain and leave the market figures empty, rather than
            # inventing a number or dropping the row.
            holdings.append(
                HoldingRead(
                    stock_id=stock.id,
                    symbol=stock.symbol,
                    name=stock.name,
                    sector=stock.sector,
                    quantity=position.quantity,
                    average_cost=position.average_cost,
                    cost_basis=position.cost_basis,
                    current_price=None,
                    price_as_of=None,
                    market_value=None,
                    unrealized_pnl=None,
                    unrealized_pct=None,
                    realized_pnl=position.realized_pnl,
                )
            )
            total_cost += position.cost_basis
            continue

        valuation = value_position(position, quote.price)
        priced_count += 1

        holdings.append(
            HoldingRead(
                stock_id=stock.id,
                symbol=stock.symbol,
                name=stock.name,
                sector=stock.sector,
                quantity=position.quantity,
                average_cost=position.average_cost,
                cost_basis=position.cost_basis,
                current_price=quote.price,
                price_as_of=quote.as_of,
                market_value=valuation.market_value,
                unrealized_pnl=valuation.unrealized_pnl,
                unrealized_pct=valuation.unrealized_pct,
                realized_pnl=position.realized_pnl,
            )
        )

        total_cost += position.cost_basis
        total_value += valuation.market_value
        total_unrealized += valuation.unrealized_pnl

    # Biggest gainers first, so the dashboard leads with what moved.
    holdings.sort(key=lambda h: h.unrealized_pnl or ZERO, reverse=True)

    total_unrealized_pct = (
        (total_unrealized / total_cost * Decimal("100")) if total_cost > ZERO else ZERO
    )

    return PortfolioSummary(
        total_cost=total_cost,
        total_value=total_value,
        total_unrealized_pnl=total_unrealized,
        total_unrealized_pct=total_unrealized_pct,
        total_realized_pnl=total_realized,
        holdings_count=len(holdings),
        priced_count=priced_count,
        holdings=holdings,
    )


def _month_ends(months: int, today: date) -> list[date]:
    """The last N month-end dates, with today as the final point.

    Today rather than this month's last day, because a month that has not
    finished yet has no month-end close — using one would mean pricing the
    portfolio at a date the market has not reached.
    """
    ends: list[date] = []
    for step in range(months - 1, 0, -1):
        year, month = today.year, today.month - step
        while month <= 0:
            month += 12
            year -= 1
        ends.append(date(year, month, monthrange(year, month)[1]))
    ends.append(today)
    return ends


def build_history(db: Session, user_id: int, months: int = 12) -> PortfolioHistory:
    """Reconstruct what the portfolio was worth at each month end.

    This is the append-only ledger earning its keep: because every buy and
    sell was kept, the position on any past date can be replayed, and
    priced with the close we cached for that date. A table that stored
    only current holdings could not answer this at all.
    """
    grouped = _trades_by_stock(db, user_id)
    if not grouped:
        return PortfolioHistory(points=[], complete_points=0)

    stock_ids = list(grouped.keys())

    # All cached closes for these stocks, in one query rather than one per
    # stock per month. Kept as sorted (date, price) lists so each lookup is
    # a binary search for "the most recent close on or before this date".
    closes: dict[int, list[tuple[date, Decimal]]] = defaultdict(list)
    rows = db.execute(
        select(PriceHistory)
        .where(PriceHistory.stock_id.in_(stock_ids))
        .order_by(PriceHistory.stock_id, PriceHistory.price_date)
    ).scalars()
    for row in rows:
        closes[row.stock_id].append((row.price_date, row.close_price))

    def price_on(stock_id: int, when: date) -> Decimal | None:
        series = closes.get(stock_id)
        if not series:
            return None
        index = bisect.bisect_right([d for d, _ in series], when)
        if index == 0:
            return None  # the stock had no cached price yet at that date
        return series[index - 1][1]

    points: list[HistoryPoint] = []
    complete = 0

    for when in _month_ends(months, date.today()):
        value = ZERO
        cost = ZERO
        priced = 0
        held = 0

        for stock_id, trades in grouped.items():
            as_of = [t for t in trades if t.transaction_date <= when]
            if not as_of:
                continue

            position = compute_position(as_of)
            if position.quantity <= ZERO:
                continue

            held += 1
            cost += position.cost_basis

            close = price_on(stock_id, when)
            if close is None:
                continue
            priced += 1
            value += position.quantity * close

        # Skip dates before the first purchase rather than drawing a flat
        # line at zero leading into the chart.
        if held == 0:
            continue

        if priced == held:
            complete += 1

        points.append(HistoryPoint(date=when, value=value, cost=cost))

    return PortfolioHistory(points=points, complete_points=complete)
