"""Database connection setup.

Two things live here: the engine (one per application) and the session
factory (one session per request).
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# The engine manages a pool of connections to Postgres. Opening a connection
# is slow, so they are reused rather than created per query.
engine = create_engine(
    settings.database_url,
    echo=settings.debug,      # print SQL when DEBUG=true
    pool_pre_ping=True,       # check a connection is alive before handing it out
)

# A factory that produces Sessions. A Session is a workspace for database
# work: it collects changes and writes them together when committed.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session, and always close it afterwards.

    FastAPI calls this for each request that needs the database. The code
    after `yield` runs once the request is finished, even if it failed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
