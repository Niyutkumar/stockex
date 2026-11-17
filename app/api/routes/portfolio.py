"""The dashboard endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_market_data
from app.db.session import get_db
from app.models.user import User
from app.schemas.portfolio import PortfolioHistory, PortfolioSummary
from app.services.market_data import MarketDataProvider
from app.services.positions import build_history, build_portfolio

router = APIRouter()


@router.get("", response_model=PortfolioSummary)
def read_portfolio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    provider: MarketDataProvider = Depends(get_market_data),
) -> PortfolioSummary:
    """Everything the dashboard needs, in one request.

    One call rather than one per holding: the front end would otherwise
    make N requests and render progressively, which looks broken while it
    loads. Prices are cached for fifteen minutes inside the provider, so
    repeated loads do not re-fetch.
    """
    return build_portfolio(db, current_user.id, provider)


@router.get("/history", response_model=PortfolioHistory)
def read_history(
    months: int = Query(default=12, ge=2, le=60),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioHistory:
    """Portfolio value at each month end, for the dashboard chart.

    Served from cached prices only — no market calls — so it stays fast
    and works offline. Populate the cache with `python -m scripts.fetch_prices`.
    """
    return build_history(db, current_user.id, months)
