"""Passwords and login tokens.

Two separate jobs that are easy to confuse:

  Hashing   turns a password into something that cannot be turned back.
            Used once at registration and once per login.
  Tokens    prove who the caller is on every later request, so the
            password is not sent again.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

ALGORITHM = "HS256"

# bcrypt silently ignores anything past 72 bytes of the password. Truncating
# explicitly makes that visible instead of surprising, and the schemas cap
# password length anyway.
BCRYPT_MAX_BYTES = 72


def hash_password(plain_password: str) -> str:
    """Hash a password for storage.

    bcrypt is deliberately slow and salts every hash, so two users with
    the same password get different stored values and brute-forcing the
    database is expensive. The plain password is never stored anywhere.
    """
    password_bytes = plain_password.encode("utf-8")[:BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a password against a stored hash.

    The hash cannot be reversed; what happens is that the candidate is
    hashed with the same salt and the results compared.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:BCRYPT_MAX_BYTES],
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        # A malformed stored hash must fail the check, not crash the request.
        return False


def create_access_token(subject: str | int, expires_minutes: int | None = None) -> str:
    """Issue a signed token identifying the user.

    The token is not encrypted — anyone can read what is inside it, so it
    carries only the user id. What it is, is *signed*: altering the payload
    invalidates the signature, so a client cannot promote itself to another
    user by editing the token.
    """
    minutes = expires_minutes or settings.access_token_expire_minutes
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(subject),          # whom the token is about
        "iat": now,                   # issued at
        "exp": now + timedelta(minutes=minutes),  # expires at
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """Return the subject of a valid token, or None.

    Returns None rather than raising for every failure mode — expired,
    tampered with, signed by someone else, or simply nonsense — because
    the caller treats all of them identically: not authenticated.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    return payload.get("sub")
