"""Stocks the user follows without owning."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.stock import Stock
from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.schemas.stock import StockRead

router = APIRouter()


@router.get("", response_model=list[StockRead])
def list_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Stock]:
    statement = (
        select(Stock)
        .join(WatchlistItem, WatchlistItem.stock_id == Stock.id)
        .where(WatchlistItem.user_id == current_user.id)
        .order_by(Stock.symbol)
    )
    return list(db.execute(statement).scalars())


@router.post("/{stock_id}", response_model=StockRead, status_code=status.HTTP_201_CREATED)
def add_to_watchlist(
    stock_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Stock:
    """Add a stock to the watchlist.

    Adding the same stock twice returns the existing entry rather than an
    error. The user's intent — "I want this on my list" — is already
    satisfied, and failing a button press that changes nothing is just
    noise. The UNIQUE constraint on (user_id, stock_id) is what makes
    this safe to do.
    """
    stock = db.get(Stock, stock_id)
    if stock is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stock not found")

    existing = db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == current_user.id,
            WatchlistItem.stock_id == stock_id,
        )
    ).scalar_one_or_none()

    if existing is None:
        db.add(WatchlistItem(user_id=current_user.id, stock_id=stock_id))
        db.commit()

    return stock


@router.delete("/{stock_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_watchlist(
    stock_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    item = db.execute(
        select(WatchlistItem).where(
            WatchlistItem.user_id == current_user.id,
            WatchlistItem.stock_id == stock_id,
        )
    ).scalar_one_or_none()

    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not on your watchlist")

    db.delete(item)
    db.commit()
