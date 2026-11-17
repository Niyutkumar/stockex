"""End-to-end API tests.

TestClient runs the real application in-process against the real
database. Only the market data provider is replaced, with a stub — so
these tests never touch the network, never depend on what the market did
today, and assert exact figures.

Being able to swap the provider like this is the payoff for injecting it
as a dependency instead of importing it inside the route.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_market_data
from app.main import app
from app.services.market_data import Quote

PRICED_ON = date(2026, 11, 17)


class StubMarketData:
    """Fake provider. Satisfies MarketDataProvider by shape, not inheritance."""

    def __init__(self, prices: dict[str, Decimal]) -> None:
        self._prices = prices

    def get_quote(self, yahoo_symbol: str) -> Quote | None:
        price = self._prices.get(yahoo_symbol)
        if price is None:
            return None
        return Quote(symbol=yahoo_symbol, price=price, as_of=PRICED_ON)

    def get_history(self, yahoo_symbol: str, period: str = "1y") -> list:
        return []


app.dependency_overrides[get_market_data] = lambda: StubMarketData(
    {"TCS.NS": Decimal("2330.00")}
)

client = TestClient(app)


def unique_email() -> str:
    return f"test-{uuid.uuid4().hex[:10]}@example.com"


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """A registered, logged-in user."""
    email = unique_email()
    password = "a-strong-password"

    created = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert created.status_code == 201, created.text

    token = client.post(
        "/api/auth/login", data={"username": email, "password": password}
    )
    assert token.status_code == 200, token.text
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


def tcs_id(headers: dict[str, str]) -> int:
    found = client.get("/api/stocks/search", params={"q": "TCS"}, headers=headers)
    assert found.status_code == 200, found.text
    return found.json()[0]["id"]


# --- meta -------------------------------------------------------------

def test_health():
    assert client.get("/health").json() == {"status": "ok"}


# --- auth -------------------------------------------------------------

def test_register_returns_user_without_password():
    body = client.post(
        "/api/auth/register",
        json={"email": unique_email(), "password": "a-strong-password"},
    ).json()
    assert "hashed_password" not in body
    assert "password" not in body


def test_duplicate_email_is_rejected():
    email = unique_email()
    payload = {"email": email, "password": "a-strong-password"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_short_password_is_rejected():
    response = client.post(
        "/api/auth/register", json={"email": unique_email(), "password": "short"}
    )
    assert response.status_code == 422


def test_wrong_password_is_rejected():
    email = unique_email()
    client.post("/api/auth/register", json={"email": email, "password": "correct-password"})
    response = client.post(
        "/api/auth/login", data={"username": email, "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_me_requires_a_token():
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_a_forged_token():
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_me_returns_the_logged_in_user(auth_headers):
    assert client.get("/api/auth/me", headers=auth_headers).status_code == 200


# --- stocks -----------------------------------------------------------

def test_search_ranks_symbol_matches_first(auth_headers):
    results = client.get(
        "/api/stocks/search", params={"q": "TCS"}, headers=auth_headers
    ).json()
    assert results[0]["symbol"] == "TCS"


def test_search_matches_company_name(auth_headers):
    results = client.get(
        "/api/stocks/search", params={"q": "Reliance"}, headers=auth_headers
    ).json()
    assert any(row["symbol"] == "RELIANCE" for row in results)


def test_search_requires_auth():
    assert client.get("/api/stocks/search", params={"q": "TCS"}).status_code == 401


# --- transactions -----------------------------------------------------

def test_future_dated_transaction_is_rejected(auth_headers):
    response = client.post(
        "/api/transactions",
        headers=auth_headers,
        json={
            "stock_id": tcs_id(auth_headers),
            "transaction_type": "BUY",
            "quantity": "10",
            "price": "2100",
            "transaction_date": str(date.today() + timedelta(days=1)),
        },
    )
    assert response.status_code == 422


def test_selling_more_than_held_is_rejected(auth_headers):
    stock_id = tcs_id(auth_headers)
    client.post(
        "/api/transactions",
        headers=auth_headers,
        json={
            "stock_id": stock_id,
            "transaction_type": "BUY",
            "quantity": "10",
            "price": "2100",
            "transaction_date": "2026-01-10",
        },
    )
    response = client.post(
        "/api/transactions",
        headers=auth_headers,
        json={
            "stock_id": stock_id,
            "transaction_type": "SELL",
            "quantity": "11",
            "price": "2500",
            "transaction_date": "2026-06-20",
        },
    )
    assert response.status_code == 400
    assert "exceeds" in response.json()["detail"]


def test_one_user_cannot_see_anothers_ledger(auth_headers):
    stock_id = tcs_id(auth_headers)
    client.post(
        "/api/transactions",
        headers=auth_headers,
        json={
            "stock_id": stock_id,
            "transaction_type": "BUY",
            "quantity": "7",
            "price": "2100",
            "transaction_date": "2026-01-10",
        },
    )

    # A different user, who has recorded nothing.
    other_email = unique_email()
    client.post(
        "/api/auth/register",
        json={"email": other_email, "password": "a-strong-password"},
    )
    other_token = client.post(
        "/api/auth/login",
        data={"username": other_email, "password": "a-strong-password"},
    ).json()["access_token"]

    other_ledger = client.get(
        "/api/transactions", headers={"Authorization": f"Bearer {other_token}"}
    ).json()
    assert other_ledger == []


# --- the dashboard, with the worked example ---------------------------

def test_portfolio_reproduces_the_tcs_worked_example(auth_headers):
    """The whole point, end to end.

    100 TCS at 2100, then 50 at 2400, then sell 60 at 2500, priced at
    2330. The same figures as the hand calculation.
    """
    stock_id = tcs_id(auth_headers)

    for payload in (
        {"transaction_type": "BUY", "quantity": "100", "price": "2100", "transaction_date": "2026-01-10"},
        {"transaction_type": "BUY", "quantity": "50", "price": "2400", "transaction_date": "2026-03-05"},
        {"transaction_type": "SELL", "quantity": "60", "price": "2500", "transaction_date": "2026-06-20"},
    ):
        response = client.post(
            "/api/transactions", headers=auth_headers, json={"stock_id": stock_id, **payload}
        )
        assert response.status_code == 201, response.text

    summary = client.get("/api/portfolio", headers=auth_headers).json()

    assert len(summary["holdings"]) == 1
    holding = summary["holdings"][0]

    assert Decimal(holding["quantity"]) == Decimal("90")
    assert Decimal(holding["cost_basis"]) == Decimal("204000")
    assert Decimal(holding["current_price"]) == Decimal("2330.00")
    assert Decimal(holding["market_value"]) == Decimal("209700")
    assert Decimal(holding["unrealized_pnl"]) == Decimal("5700")
    assert Decimal(holding["realized_pnl"]) == Decimal("24000")

    assert Decimal(summary["total_value"]) == Decimal("209700")
    assert Decimal(summary["total_realized_pnl"]) == Decimal("24000")
    assert Decimal(summary["total_unrealized_pnl"]) == Decimal("5700")


def test_portfolio_is_empty_for_a_new_user(auth_headers):
    summary = client.get("/api/portfolio", headers=auth_headers).json()
    assert summary["holdings"] == []
    assert Decimal(summary["total_value"]) == Decimal("0")


def test_holding_still_appears_when_the_price_feed_fails(auth_headers):
    """RELIANCE is not in the stub's price list, so no quote comes back.

    The holding must still be listed, with the figures we know for
    certain and nulls for the market ones — not dropped, and not given
    an invented price.
    """
    found = client.get(
        "/api/stocks/search", params={"q": "RELIANCE"}, headers=auth_headers
    ).json()
    stock_id = found[0]["id"]

    client.post(
        "/api/transactions",
        headers=auth_headers,
        json={
            "stock_id": stock_id,
            "transaction_type": "BUY",
            "quantity": "5",
            "price": "1300",
            "transaction_date": "2026-02-01",
        },
    )

    summary = client.get("/api/portfolio", headers=auth_headers).json()
    holding = next(h for h in summary["holdings"] if h["symbol"] == "RELIANCE")

    assert Decimal(holding["cost_basis"]) == Decimal("6500")
    assert holding["current_price"] is None
    assert holding["market_value"] is None
    assert summary["priced_count"] == 0


# --- watchlist --------------------------------------------------------

def test_watchlist_add_list_and_remove(auth_headers):
    stock_id = tcs_id(auth_headers)

    assert client.post(f"/api/watchlist/{stock_id}", headers=auth_headers).status_code == 201
    # Adding twice is accepted, not an error: the intent is already met.
    assert client.post(f"/api/watchlist/{stock_id}", headers=auth_headers).status_code == 201

    listed = client.get("/api/watchlist", headers=auth_headers).json()
    assert [row["symbol"] for row in listed] == ["TCS"]

    assert client.delete(f"/api/watchlist/{stock_id}", headers=auth_headers).status_code == 204
    assert client.get("/api/watchlist", headers=auth_headers).json() == []
    assert client.delete(f"/api/watchlist/{stock_id}", headers=auth_headers).status_code == 404
