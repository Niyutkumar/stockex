"""The price_history table — daily market prices we have already fetched.

Without this, drawing a chart of portfolio value over a year would mean
hundreds of API calls every time the page loads. With it, one fetch per
stock per day and everything after that is a local database read.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class PriceHistory(Base, TimestampMixin):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True)

    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The trading day this price belongs to.
    price_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Named *_price rather than open/high/low/close for two reasons:
    # `open` is a Python builtin, and several of these are reserved words
    # in SQL. Avoiding both collisions costs nothing.
    #
    # Only the close is required. yfinance returns all of them, so we
    # store them now — candlestick charts later need them, and adding
    # columns to a table with data in it is more work than filling them.
    open_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    high_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    low_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    close_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # BigInteger, not Integer: a plain integer caps around 2.1 billion,
    # and heavily traded counters can exceed that in a single session.
    volume: Mapped[int | None] = mapped_column(BigInteger)

    __table_args__ = (
        # One price row per stock per day. This constraint is what makes
        # re-running a price fetch safe: a duplicate insert is rejected
        # by the database rather than silently doubling the data.
        UniqueConstraint("stock_id", "price_date", name="uq_price_history_stock_date"),
    )

    def __repr__(self) -> str:
        return f"<PriceHistory stock_id={self.stock_id} {self.price_date} close={self.close_price}>"
