"""Tests for the portfolio history endpoint.

Prices are inserted straight into price_history rather than fetched, so
the expected values are fixed and no network call happens.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.price_history import PriceHistory
from app.models.stock import Stock

client = TestClient(app)


def unique_email():
    return f"hist-{uuid.uuid4().hex[:10]}@example.com"


@pytest.fixture
def headers():
    email = unique_email()
    client.post("/api/auth/register", json={"email": email, "password": "a-strong-password"})
    token = client.post(
        "/api/auth/login", data={"username": email, "password": "a-strong-password"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def tcs_with_prices():
    """TCS, with a cached close on a handful of past dates."""
    with SessionLocal() as session:
        stock = session.execute(select(Stock).where(Stock.symbol == "TCS")).scalar_one()
        wanted = {
            date(2026, 1, 31): Decimal("2150.00"),
            date(2026, 2, 28): Decimal("2200.00"),
            date(2026, 3, 31): Decimal("2300.00"),
            date(2026, 4, 30): Decimal("2250.00"),
        }
        existing = {
            row.price_date
            for row in session.execute(
                select(PriceHistory).where(PriceHistory.stock_id == stock.id)
            ).scalars()
        }
        for when, close in wanted.items():
            if when not in existing:
                session.add(
                    PriceHistory(stock_id=stock.id, price_date=when, close_price=close)
                )
        session.commit()
        return stock.id


def test_history_is_empty_without_trades(headers):
    body = client.get("/api/portfolio/history", headers=headers).json()
    assert body["points"] == []


def test_history_values_a_past_position(headers, tcs_with_prices):
    """100 shares bought in January, priced at each month end."""
    client.post(
        "/api/transactions",
        headers=headers,
        json={
            "stock_id": tcs_with_prices,
            "transaction_type": "BUY",
            "quantity": "100",
            "price": "2100",
            "transaction_date": "2026-01-10",
        },
    )

    body = client.get("/api/portfolio/history?months=12", headers=headers).json()
    points = {p["date"]: Decimal(p["value"]) for p in body["points"]}

    # 100 shares at each month's cached close.
    assert points["2026-01-31"] == Decimal("215000")
    assert points["2026-02-28"] == Decimal("220000")
    assert points["2026-03-31"] == Decimal("230000")
    assert points["2026-04-30"] == Decimal("225000")


def test_history_skips_dates_before_the_first_purchase(headers, tcs_with_prices):
    client.post(
        "/api/transactions",
        headers=headers,
        json={
            "stock_id": tcs_with_prices,
            "transaction_type": "BUY",
            "quantity": "10",
            "price": "2100",
            "transaction_date": "2026-03-05",
        },
    )
    body = client.get("/api/portfolio/history?months=12", headers=headers).json()
    dates = [p["date"] for p in body["points"]]
    # Nothing was held in January, so January must not appear as a zero.
    assert "2026-01-31" not in dates
    assert "2026-03-31" in dates


def test_history_reflects_a_sale(headers, tcs_with_prices):
    for payload in (
        {"transaction_type": "BUY", "quantity": "100", "price": "2100", "transaction_date": "2026-01-10"},
        {"transaction_type": "SELL", "quantity": "60", "price": "2250", "transaction_date": "2026-03-02"},
    ):
        client.post(
            "/api/transactions",
            headers=headers,
            json={"stock_id": tcs_with_prices, **payload},
        )

    body = client.get("/api/portfolio/history?months=12", headers=headers).json()
    points = {p["date"]: Decimal(p["value"]) for p in body["points"]}

    # January: all 100 held.  March: 40 left after the sale.
    assert points["2026-01-31"] == Decimal("215000")
    assert points["2026-03-31"] == Decimal("92000")  # 40 * 2300


def test_history_rejects_a_silly_range(headers):
    assert client.get("/api/portfolio/history?months=1", headers=headers).status_code == 422
    assert client.get("/api/portfolio/history?months=600", headers=headers).status_code == 422
