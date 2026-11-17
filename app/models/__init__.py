"""Model registry.

SQLAlchemy only knows about a table if its class has been imported —
importing is what registers it on Base. Alembic asks Base what tables
should exist, so every model must be imported here or it is invisible to
the migration and gets silently skipped.

The unused-import warnings from the editor are expected: the import
itself is the point.
"""

from app.models.price_history import PriceHistory
from app.models.stock import Stock
from app.models.transaction import Transaction
from app.models.user import User
from app.models.watchlist import WatchlistItem

__all__ = [
    "PriceHistory",
    "Stock",
    "Transaction",
    "User",
    "WatchlistItem",
]
