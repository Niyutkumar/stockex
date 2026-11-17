"""Collects every route group into one router mounted at /api.

Each module owns its own URL prefix and tag, so adding a feature means
adding one file and one line here.
"""

from fastapi import APIRouter

from app.api.routes import auth, portfolio, stocks, transactions, watchlist

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])
api_router.include_router(
    transactions.router, prefix="/transactions", tags=["transactions"]
)
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
