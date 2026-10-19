"""Engine / session management."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.db")

_connect_args: dict[str, object] = {}
_engine_kwargs: dict[str, object] = {"echo": settings.db_echo, "future": True}

if settings.is_sqlite:
    # SQLite needs the check disabled for concurrent FastAPI workers, and we
    # keep the event loop free by using the default sync driver.
    _connect_args["check_same_thread"] = False
    database_path = settings.database_url.replace("sqlite:///", "")
    from pathlib import Path

    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
else:
    _engine_kwargs.update(
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
    )

engine: Engine = create_engine(
    settings.database_url, connect_args=_connect_args, **_engine_kwargs
)

if settings.is_sqlite:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record) -> None:  # pragma: no cover - driver hook
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()