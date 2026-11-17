"""Request and response shapes for users.

These are Pydantic models, not database models, and the distinction is
the point: the database model holds `hashed_password`, and no schema
here exposes it. Returning an ORM object directly from an endpoint is how
password hashes end up in API responses.
"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """What a client sends to register."""

    email: EmailStr
    # 8 minimum as a floor on guessability; 72 because bcrypt ignores
    # anything beyond that, so accepting more would be a lie.
    password: str = Field(min_length=8, max_length=72)
    full_name: str | None = Field(default=None, max_length=120)


class UserRead(BaseModel):
    """What the API returns about a user. Note the absence of any password."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    is_active: bool
