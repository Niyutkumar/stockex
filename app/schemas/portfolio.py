"""Response shapes for the dashboard."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class HoldingRead(BaseModel):
    """One stock currently held, priced at the market."""

    stock_id: int
    symbol: str
    name: str
    sector: str | None

    quantity: Decimal
    average_cost: Decimal
    cost_basis: Decimal

    current_price: Decimal | None
    price_as_of: date | None

    market_value: Decimal | None
    unrealized_pnl: Decimal | None
    unrealized_pct: Decimal | None
    realized_pnl: Decimal


class PortfolioSummary(BaseModel):
    """The whole portfolio, and the totals the dashboard leads with.

    Realized and unrealized are reported separately, never added into one
    headline figure. One is money actually banked and fixed forever; the
    other moves every day with the market.
    """

    total_cost: Decimal
    total_value: Decimal
    total_unrealized_pnl: Decimal
    total_unrealized_pct: Decimal
    total_realized_pnl: Decimal

    holdings_count: int
    priced_count: int  # how many holdings we could get a price for

    holdings: list[HoldingRead]


class HistoryPoint(BaseModel):
    """Portfolio value on one date, reconstructed from the ledger."""

    date: date
    value: Decimal
    cost: Decimal


class PortfolioHistory(BaseModel):
    """A value series for the dashboard chart."""

    points: list[HistoryPoint]
    # How many month-ends had a usable price for every holding. A point
    # built from partial prices understates the portfolio, so the UI can
    # warn rather than draw a misleading dip.
    complete_points: int
