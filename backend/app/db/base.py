"""SQLAlchemy declarative base and portable column helpers."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData, TypeDecorator, Uuid, func
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Explicit naming convention keeps Alembic autogenerate deterministic and
# lets us add/drop constraints safely across PostgreSQL and SQLite.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    """Timezone aware UTC now (used for Python side defaults)."""
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """`DateTime` that always round-trips timezone aware UTC datetimes.

    SQLite has no native timezone support and silently drops ``tzinfo`` even
    for ``DateTime(timezone=True)``. Naive values coming back from the driver
    would break comparisons against ``datetime.now(UTC)``, so we re-attach UTC
    on the way out and normalise on the way in.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def uuid_pk() -> Mapped[uuid.UUID]:
    """UUID primary key column."""
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


def created_at_column() -> Mapped[datetime]:
    return mapped_column(UTCDateTime, nullable=False, server_default=func.now(), default=utcnow)


def updated_at_column() -> Mapped[datetime]:
    return mapped_column(
        UTCDateTime,
        nullable=False,
        server_default=func.now(),
        default=utcnow,
        onupdate=utcnow,
    )