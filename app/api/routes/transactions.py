"""Recording buys and sells."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.stock import Stock
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import (
    TransactionCreate,
    TransactionRead,
    TransactionReadWithStock,
)
from app.services.portfolio import OversoldError, Trade, compute_position

router = APIRouter()


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Transaction:
    """Record a buy or a sell.

    A SELL is checked against the shares actually held at that date before
    anything is written. Without this you could sell 100 shares you never
    owned, and every figure on the dashboard would be quietly wrong from
    then on.
    """
    stock = db.get(Stock, payload.stock_id)
    if stock is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stock not found")

    if payload.transaction_type == "SELL":
        existing = db.execute(
            select(Transaction).where(
                Transaction.user_id == current_user.id,
                Transaction.stock_id == payload.stock_id,
            )
        ).scalars()

        trades = [
            Trade(
                transaction_type=row.transaction_type,
                quantity=row.quantity,
                price=row.price,
                transaction_date=row.transaction_date,
                id=row.id,
            )
            for row in existing
        ]
        # id=0 sorts this candidate before same-day existing rows, which is
        # the conservative choice: if it only balances when placed last, it
        # is rejected.
        trades.append(
            Trade(
                transaction_type="SELL",
                quantity=payload.quantity,
                price=payload.price,
                transaction_date=payload.transaction_date,
                id=0,
            )
        )

        try:
            compute_position(trades)
        except OversoldError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error

    transaction = Transaction(
        user_id=current_user.id,
        stock_id=payload.stock_id,
        transaction_type=payload.transaction_type,
        quantity=payload.quantity,
        price=payload.price,
        transaction_date=payload.transaction_date,
        notes=payload.notes,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("", response_model=list[TransactionReadWithStock])
def list_transactions(
    stock_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TransactionReadWithStock]:
    """The ledger, newest first.

    Filtered by user_id on every query. This is the line that stops one
    user reading another's trades, and it belongs in every query that
    touches user-owned data.
    """
    statement = (
        select(Transaction, Stock)
        .join(Stock, Stock.id == Transaction.stock_id)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .limit(limit)
    )
    if stock_id is not None:
        statement = statement.where(Transaction.stock_id == stock_id)

    return [
        TransactionReadWithStock(
            id=transaction.id,
            stock_id=transaction.stock_id,
            transaction_type=transaction.transaction_type,
            quantity=transaction.quantity,
            price=transaction.price,
            transaction_date=transaction.transaction_date,
            notes=transaction.notes,
            symbol=stock.symbol,
            stock_name=stock.name,
        )
        for transaction, stock in db.execute(statement).all()
    ]


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Remove a ledger entry.

    This sits in slight tension with the append-only principle, and the
    distinction is worth being clear about: the ledger is append-only for
    *business events* — a sale is never an edit of a purchase. But a
    mistyped entry was never a real event, and a user needs to fix a
    typo. Accounting systems do this with a reversing entry; for a
    personal tracker, deleting the wrong row is the honest equivalent.

    The user_id filter is what stops anyone deleting someone else's row
    by guessing an id.
    """
    transaction = db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if transaction is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")

    db.delete(transaction)
    db.commit()
