"""The stocks table — the master list of tradable securities."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Stock(Base, TimestampMixin):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True)

    # The exchange's own symbol, e.g. "RELIANCE". Searched constantly, so indexed.
    symbol: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False)

    exchange: Mapped[str] = mapped_column(String(10), default="NSE", nullable=False)

    # Yahoo needs its own suffix ("RELIANCE.NS"). Kept in a separate column so
    # one data provider's naming never contaminates our own symbol field.
    # If we swap providers later, only this column and one module change.
    yahoo_symbol: Mapped[str | None] = mapped_column(String(40), index=True)

    # Useful for grouping the dashboard by sector later.
    sector: Mapped[str | None] = mapped_column(String(100))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<Stock {self.symbol} ({self.exchange})>"
