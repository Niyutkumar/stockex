"""The users table — people who can log in."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    # unique=True: Postgres itself rejects a duplicate email, so two accounts
    # can never share one even if the application code has a bug.
    # index=True: logging in looks users up by email, so this must be fast.
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    # `str | None` means the column is allowed to be empty.
    full_name: Mapped[str | None] = mapped_column(String(120))

    # NEVER store the password itself. This holds a one-way hash of it.
    # The column name says so, so nobody is tempted to put a password here.
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Lets you disable an account without deleting it — deleting a user would
    # orphan every transaction they ever recorded.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
