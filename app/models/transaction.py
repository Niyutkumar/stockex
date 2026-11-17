"""The transactions table — the append-only ledger of buys and sells.

Rows here are never edited and never deleted. Selling appends a SELL row.
Current holdings are calculated by replaying these rows, never stored,
because storing only the current position destroys the history that the
dashboard and the analytics layer depend on.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)

    # CASCADE: delete a user and their ledger goes with them. A ledger
    # belonging to nobody is meaningless.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # RESTRICT is the opposite choice, deliberately: Postgres refuses to
    # delete a stock while transactions still refer to it.
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # "BUY" or "SELL". The check constraint below makes anything else
    # impossible to store — including a typo like "buy" or "PURCHASE".
    transaction_type: Mapped[str] = mapped_column(String(4), nullable=False)

    # Numeric, never Float. Floats cannot represent decimals exactly and
    # the error compounds across thousands of rows. 4 decimal places
    # allows for fractional units.
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    # Price per share, in rupees.
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # A date, not a timestamp. Past trades are entered from a broker
    # statement, where the day is known and the second is not. Invented
    # precision is worse than none. Same-day trades are ordered by id.
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Optional free text. Text rather than String(n): no sensible maximum.
    notes: Mapped[str | None] = mapped_column(Text)

    # Deliberately absent: a total_value column. It is quantity * price,
    # and storing a derived value creates two sources of truth that drift.

    __table_args__ = (
        # The strings inside CheckConstraint are raw SQL, passed straight
        # through to Postgres. SQLAlchemy does not translate them.
        CheckConstraint(
            "transaction_type IN ('BUY', 'SELL')",
            name="ck_transactions_type",
        ),
        CheckConstraint(
            "quantity > 0",
            name="ck_transactions_quantity_positive",
        ),
        CheckConstraint(
            "price >= 0",
            name="ck_transactions_price_non_negative",
        ),
        # One index covering the query the app runs constantly: this
        # user's trades in this stock, in date order — exactly what
        # computing a position requires.
        Index(
            "ix_transactions_user_stock_date",
            "user_id",
            "stock_id",
            "transaction_date",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction {self.transaction_type} {self.quantity} "
            f"stock_id={self.stock_id} @ {self.price} on {self.transaction_date}>"
        )
