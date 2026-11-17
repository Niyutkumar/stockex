"""Alembic environment.

This file is the bridge between Alembic and our application. It does two
jobs: tell Alembic where the database is, and tell it what the schema is
supposed to look like.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base

# Importing app.models runs all five model files, which is what registers
# them on Base. Without this line Base.metadata is empty and autogenerate
# produces a migration that creates nothing — with no error.
import app.models  # noqa: F401

config = context.config

# The one place the database URL enters Alembic: from .env, via settings.
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# "What the schema should be", for Alembic to compare against the real
# database. Base.metadata is the registry every model attached itself to.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to a file instead of running it.

    Useful when a DBA has to review or apply the SQL by hand. Not how we
    normally run migrations, but worth keeping.
    """
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the database and run the migrations against it."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Notice when a column's TYPE changes, not just when columns
            # are added or removed. Off by default, and its absence is a
            # common source of migrations that silently miss a change.
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
