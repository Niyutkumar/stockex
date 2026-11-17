"""The login response."""

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    # "bearer" is the HTTP standard scheme name: the client sends
    # `Authorization: Bearer <token>` on subsequent requests.
    token_type: str = "bearer"
