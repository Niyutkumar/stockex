"""Registration and login."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """Create an account.

    The uniqueness check here gives a clean 409 instead of a database
    error page. The UNIQUE constraint on the column is still the real
    guarantee — this check and the insert are not atomic, so two
    simultaneous registrations could both pass it, and the database is
    what actually stops the duplicate.
    """
    existing = db.execute(
        select(User).where(User.email == payload.email)
    ).scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # loads the database-generated id and timestamps
    return user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Exchange email and password for a token.

    The form field is called `username` because that is what the OAuth2
    password-flow standard specifies; we put the email in it. Using the
    standard shape is what makes the Authorize button in /docs work, and
    what standard client libraries expect.
    """
    user = db.execute(
        select(User).where(User.email == form_data.username)
    ).scalar_one_or_none()

    # One message for both "no such account" and "wrong password". Telling
    # them apart would let anyone test which emails are registered.
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is disabled",
        )

    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Who am I? Used by the front end to confirm a stored token is valid."""
    return current_user
