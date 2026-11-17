"""Stock search and quotes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_market_data
from app.db.session import get_db
from app.models.stock import Stock
from app.models.user import User
from app.schemas.stock import QuoteRead, StockRead
from app.services.market_data import MarketDataProvider

router = APIRouter()


@router.get("/search", response_model=list[StockRead])
def search_stocks(
    q: str = Query(min_length=1, max_length=50, description="Symbol or company name"),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Stock]:
    """Search the local stock list.

    Searching our own table rather than calling an API on every keystroke:
    this returns in milliseconds, works offline, and cannot be rate
    limited. It is the reason the `stocks` table exists at all.
    """
    term = q.strip()
    pattern = f"%{term}%"
    prefix = f"{term}%"

    # Symbols starting with the term rank above mid-word matches, so
    # typing "TCS" puts TCS first rather than some company with "tcs"
    # buried in its name.
    relevance = case((Stock.symbol.ilike(prefix), 0), else_=1)

    statement = (
        select(Stock)
        .where(Stock.is_active.is_(True))
        .where(or_(Stock.symbol.ilike(pattern), Stock.name.ilike(pattern)))
        .order_by(relevance, Stock.symbol)
        .limit(limit)
    )
    return list(db.execute(statement).scalars())


@router.get("/{stock_id}/quote", response_model=QuoteRead)
def read_quote(
    stock_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    provider: MarketDataProvider = Depends(get_market_data),
) -> QuoteRead:
    """Current (delayed) price for one stock."""
    stock = db.get(Stock, stock_id)
    if stock is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Stock not found")

    quote = provider.get_quote(stock.yahoo_symbol or f"{stock.symbol}.NS")
    if quote is None:
        # 503, not 404: the stock exists, the upstream feed is unavailable.
        # The distinction matters to a client deciding whether to retry.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Market data is unavailable for this stock right now",
        )

    return QuoteRead(symbol=stock.symbol, price=quote.price, as_of=quote.as_of)
