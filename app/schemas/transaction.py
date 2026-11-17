"""Request and response shapes for ledger entries."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionCreate(BaseModel):
    """What a client sends to record a buy or a sell."""

    stock_id: int
    # Literal rather than str: FastAPI rejects anything else before the
    # request reaches our code, and the generated docs list the two valid
    # values. The database has a CHECK constraint saying the same thing —
    # two layers, because the database also guards against scripts and
    # manual inserts that never pass through this schema.
    transaction_type: Literal["BUY", "SELL"]

    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    transaction_date: date
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("transaction_date")
    @classmethod
    def not_in_the_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("transaction_date cannot be in the future")
        return value


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stock_id: int
    transaction_type: str
    quantity: Decimal
    price: Decimal
    transaction_date: date
    notes: str | None


class TransactionReadWithStock(TransactionRead):
    """A ledger entry with the stock's symbol attached, for list views."""

    symbol: str
    stock_name: str
