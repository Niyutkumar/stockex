"""Position calculation.

Pure functions. No database, no network, no framework. Give it a list of
trades and it returns what is held, what it cost, and what profit has
been booked.

Keeping this layer pure is deliberate: it is the only part of StockEx
where a bug silently produces wrong money, and pure functions can be
tested exhaustively without a database. See tests/test_portfolio.py.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

BUY = "BUY"
SELL = "SELL"

ZERO = Decimal("0")


@dataclass(frozen=True)
class Trade:
    """One row of the ledger, as this module needs to see it."""

    transaction_type: str
    quantity: Decimal
    price: Decimal
    transaction_date: date
    id: int = 0


@dataclass(frozen=True)
class Lot:
    """Shares bought together at one price, or what remains of them."""

    quantity: Decimal
    price: Decimal

    @property
    def cost(self) -> Decimal:
        return self.quantity * self.price


@dataclass(frozen=True)
class Position:
    """What a user currently holds in one stock, derived from its trades."""

    quantity: Decimal
    cost_basis: Decimal
    average_cost: Decimal
    realized_pnl: Decimal
    lots: tuple[Lot, ...]


@dataclass(frozen=True)
class Valuation:
    """A position priced at the current market."""

    position: Position
    current_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    unrealized_pct: Decimal
    total_pnl: Decimal


class OversoldError(ValueError):
    """Raised when a SELL exceeds the shares held at that point."""


def compute_position(trades: list[Trade]) -> Position:
    """Replay a stock's trades in order and return the resulting position.

    Cost basis is FIFO: the oldest shares are sold first, because that is
    what Indian tax rules require. The choice is not cosmetic — selling 60
    of 150 TCS shares bought at two prices gives Rs 24,000 realized profit
    under FIFO and Rs 18,000 under average cost.
    """
    # Date first, then id, so two trades on the same day stay in the order
    # they were entered. Without the id tiebreak the result would depend on
    # whatever order the database happened to return rows in.
    ordered = sorted(trades, key=lambda t: (t.transaction_date, t.id))

    open_lots: deque[list[Decimal]] = deque()  # [quantity, price], mutable
    realized = ZERO

    for trade in ordered:
        if trade.transaction_type == BUY:
            open_lots.append([trade.quantity, trade.price])
            continue

        if trade.transaction_type != SELL:
            raise ValueError(f"Unknown transaction type: {trade.transaction_type!r}")

        remaining = trade.quantity
        while remaining > ZERO:
            if not open_lots:
                raise OversoldError(
                    f"SELL of {trade.quantity} on {trade.transaction_date} "
                    f"exceeds the shares held at that date"
                )

            lot = open_lots[0]
            taken = min(lot[0], remaining)

            # Profit on the shares sold out of THIS lot: what they sold for
            # minus what they were bought for.
            realized += taken * (trade.price - lot[1])

            lot[0] -= taken
            remaining -= taken

            if lot[0] == ZERO:
                open_lots.popleft()

    lots = tuple(Lot(quantity=q, price=p) for q, p in open_lots)
    quantity = sum((lot.quantity for lot in lots), ZERO)
    cost_basis = sum((lot.cost for lot in lots), ZERO)
    average_cost = (cost_basis / quantity) if quantity > ZERO else ZERO

    return Position(
        quantity=quantity,
        cost_basis=cost_basis,
        average_cost=average_cost,
        realized_pnl=realized,
        lots=lots,
    )


def value_position(position: Position, current_price: Decimal) -> Valuation:
    """Price a position at the current market.

    Realized and unrealized are kept separate on purpose. Realized profit
    is money actually made and never changes again. Unrealized moves every
    day with the market. Adding them together without saying so is how
    portfolio trackers end up lying to people.
    """
    market_value = position.quantity * current_price
    unrealized = market_value - position.cost_basis

    unrealized_pct = (
        (unrealized / position.cost_basis * Decimal("100"))
        if position.cost_basis > ZERO
        else ZERO
    )

    return Valuation(
        position=position,
        current_price=current_price,
        market_value=market_value,
        unrealized_pnl=unrealized,
        unrealized_pct=unrealized_pct,
        total_pnl=unrealized + position.realized_pnl,
    )
