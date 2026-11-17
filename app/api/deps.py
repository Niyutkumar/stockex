"""Shared dependencies for the API layer.

FastAPI's dependency injection: a route declares what it needs as a
parameter default, and FastAPI resolves it before the route runs.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services.market_data import MarketDataProvider, market_data

# tokenUrl tells the generated /docs page where to send the login form,
# which is what makes the "Authorize" button there work.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the logged-in user from the Authorization header.

    Any route that takes this as a dependency is automatically protected:
    without a valid token the request never reaches the route body.

    Every failure returns the same 401 with the same message. Saying
    "no such user" rather than "wrong password" would let an attacker
    discover which email addresses are registered.
    """
    subject = decode_access_token(token)
    if subject is None:
        raise CREDENTIALS_ERROR

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise CREDENTIALS_ERROR

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR

    return user


def get_market_data() -> MarketDataProvider:
    """The market data provider, as a dependency.

    Injected rather than imported directly so a test can substitute a
    fake provider and never touch the network.
    """
    return market_data
