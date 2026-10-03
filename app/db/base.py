"""Shared foundations for every database model.

`Base` is the parent class all models inherit from. SQLAlchemy uses it to
keep a registry of every table, which is how Alembic later works out what
the schema should look like.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Parent class for all models."""


class TimestampMixin:
    """Adds created_at / updated_at to any model that inherits it.

    Almost every table wants these, and writing them out five times invites
    inconsistency. `server_default=func.now()` means Postgres fills the value
    in itself, so it is correct even if a row is inserted by hand in psql.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
