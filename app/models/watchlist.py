"""The watchlist table — stocks a user follows but does not own.

Kept separate from transactions because interest is not ownership. A row
here carries no financial history, only a bookmark.
"""

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class WatchlistItem(Base, TimestampMixin):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # CASCADE here, unlike transactions, where this is RESTRICT. A
    # watchlist row is only a bookmark — if the stock goes, nothing of
    # value is lost. A transaction records money that moved, so it must
    # never be stripped of what it refers to.
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        # The COMBINATION is unique, not either column alone: one user
        # cannot add the same stock twice, but many users can watch TCS.
        UniqueConstraint("user_id", "stock_id", name="uq_watchlist_user_stock"),
    )

    def __repr__(self) -> str:
        return f"<WatchlistItem user_id={self.user_id} stock_id={self.stock_id}>"
