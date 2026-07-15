"""Alembic migration environment.

Deliberately imports the application's own `Settings` and declarative
`Base` rather than hardcoding a connection string or duplicating table
definitions - this guarantees migrations always target whatever database
`.env` currently points at, and that `alembic revision --autogenerate`
compares against the real, current set of models.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# --- Make the `app` package importable when Alembic is run from backend/ ---
import os
import sys

sys.path.insert(0, os.getcwd())

from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402

# Import every model module so its table is registered on Base.metadata
# before autogenerate compares against it.
from app.models import chat_message, doctor, followup, interaction, product  # noqa: E402,F401

config = context.config

# Inject the real DATABASE_URL from application settings (i.e. .env) instead
# of relying on a hardcoded value in alembic.ini.
#
# `%` must be escaped as `%%` here: alembic.ini is parsed by Python's
# configparser, which treats a bare `%` as the start of its own
# interpolation syntax (e.g. `%(section)s`). A DATABASE_URL containing a
# percent-encoded password character - `%40` for `@`, for example - will
# otherwise crash with "invalid interpolation syntax" before a single
# migration command runs. This has no effect on the actual connection
# string SQLAlchemy sees; it only satisfies configparser's own escaping
# rules for this one config-loading step.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (emits raw SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live DB connection (the normal path)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # detect column type changes, not just add/drop
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
