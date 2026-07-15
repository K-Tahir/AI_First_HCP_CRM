"""Database engine and session factory."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

# Connection pooling tuning: SQLite is a single local file (pooling tuning is
# irrelevant there and can even cause issues), but MySQL/Postgres are real
# network servers that silently close idle connections after a timeout
# (MySQL's default `wait_timeout` is 8 hours, but many hosted MySQL
# providers set it much lower). Without `pool_recycle`, a connection that's
# gone stale server-side produces a confusing "MySQL server has gone away"
# error the first time it's reused. `pool_pre_ping` adds a lightweight
# `SELECT 1` health check before handing out a pooled connection, which
# catches this proactively and transparently reconnects instead of failing
# the request.
_engine_kwargs = {"pool_pre_ping": True, "future": True}
if not settings.is_sqlite:
    _engine_kwargs.update(
        pool_recycle=1800,  # recycle connections older than 30 minutes
        pool_size=10,
        max_overflow=20,
    )

engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables - but only for the zero-setup SQLite fallback.

    On MySQL/Postgres, schema is owned exclusively by Alembic
    (`alembic upgrade head` - see backend/alembic/README.md). Deliberately
    NOT calling `create_all()` there too, even though it's idempotent: with
    two sources of truth for schema, a model change that isn't yet migrated
    could get silently patched in by `create_all()`, masking a missing
    migration until it surfaces confusingly later (e.g. in a teammate's
    environment, or in production). Alembic being the *only* thing that can
    create/alter tables on a real database keeps that failure mode from
    happening at all.
    """
    from app.models import doctor, interaction, followup, product, chat_message  # noqa: F401

    from app.db.base import Base

    if settings.is_sqlite:
        Base.metadata.create_all(bind=engine)
    else:
        logger.info(
            "MySQL/Postgres detected - skipping create_all(); schema is managed by Alembic. "
            "Run `alembic upgrade head` from backend/ if you haven't yet."
        )
