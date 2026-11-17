"""Tests for the position engine.

The worked example is the real one from the design session: TCS bought
twice and sold once. If FIFO is implemented wrongly these numbers change,
which is exactly what a test is for.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.services.portfolio import (
    BUY,
    SELL,
    OversoldError,
    Trade,
    compute_position,
    value_position,
)


def d(value: str) -> Decimal:
    return Decimal(value)


TCS_TRADES = [
    Trade(BUY, d("100"), d("2100"), date(2026, 1, 10), id=1),
    Trade(BUY, d("50"), d("2400"), date(2026, 3, 5), id=2),
    Trade(SELL, d("60"), d("2500"), date(2026, 6, 20), id=3),
]


def test_quantity_held():
    assert compute_position(TCS_TRADES).quantity == d("90")


def test_realized_profit_uses_fifo():
    # The 60 sold come out of the January lot at 2100, not an average of
    # 2200. 60 * (2500 - 2100) = 24,000.
    assert compute_position(TCS_TRADES).realized_pnl == d("24000")


def test_remaining_lots_keep_their_own_prices():
    lots = compute_position(TCS_TRADES).lots
    assert [(lot.quantity, lot.price) for lot in lots] == [
        (d("40"), d("2100")),
        (d("50"), d("2400")),
    ]


def test_cost_basis_of_remaining_shares():
    # 40 * 2100 + 50 * 2400 = 204,000
    assert compute_position(TCS_TRADES).cost_basis == d("204000")


def test_valuation_at_current_price():
    valuation = value_position(compute_position(TCS_TRADES), d("2330"))
    assert valuation.market_value == d("209700")      # 90 * 2330
    assert valuation.unrealized_pnl == d("5700")      # 209700 - 204000
    assert valuation.total_pnl == d("29700")          # 5700 + 24000 realized


def test_order_of_input_does_not_matter():
    # Trades are sorted internally, so a database returning rows in a
    # different order must not change the answer.
    shuffled = [TCS_TRADES[2], TCS_TRADES[0], TCS_TRADES[1]]
    assert compute_position(shuffled) == compute_position(TCS_TRADES)


def test_sell_spanning_two_lots():
    trades = [
        Trade(BUY, d("10"), d("100"), date(2026, 1, 1), id=1),
        Trade(BUY, d("10"), d("200"), date(2026, 2, 1), id=2),
        Trade(SELL, d("15"), d("300"), date(2026, 3, 1), id=3),
    ]
    position = compute_position(trades)
    # 10 from the first lot: 10 * (300-100) = 2000
    #  5 from the second:     5 * (300-200) = 500
    assert position.realized_pnl == d("2500")
    assert position.quantity == d("5")
    assert position.average_cost == d("200")


def test_selling_everything_leaves_a_flat_position():
    trades = [
        Trade(BUY, d("10"), d("100"), date(2026, 1, 1), id=1),
        Trade(SELL, d("10"), d("150"), date(2026, 2, 1), id=2),
    ]
    position = compute_position(trades)
    assert position.quantity == d("0")
    assert position.cost_basis == d("0")
    assert position.average_cost == d("0")
    assert position.realized_pnl == d("500")


def test_overselling_is_rejected():
    trades = [
        Trade(BUY, d("10"), d("100"), date(2026, 1, 1), id=1),
        Trade(SELL, d("11"), d("150"), date(2026, 2, 1), id=2),
    ]
    with pytest.raises(OversoldError):
        compute_position(trades)


def test_no_trades_is_an_empty_position():
    position = compute_position([])
    assert position.quantity == d("0")
    assert position.lots == ()


def test_decimal_arithmetic_stays_exact():
    # The float trap: 0.1 + 0.2 != 0.3. With Decimal it does.
    trades = [
        Trade(BUY, d("3"), d("0.1"), date(2026, 1, 1), id=1),
    ]
    assert compute_position(trades).cost_basis == d("0.3")
