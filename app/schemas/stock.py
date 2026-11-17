"""Request and response shapes for stocks."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class StockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    name: str
    exchange: str
    sector: str | None


class QuoteRead(BaseModel):
    """A current (delayed) market price."""

    symbol: str
    price: Decimal
    as_of: date
    # Honest about what this is. Free market data is delayed by roughly
    # fifteen minutes, and the UI should say so rather than imply live
    # prices.
    delayed: bool = True
