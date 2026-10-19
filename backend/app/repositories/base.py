"""Generic repository helpers — keeps SQL out of the service layer."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.base import Base

Model = TypeVar("Model", bound=Base)


class BaseRepository(Generic[Model]):
    model: type[Model]

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------- reading
    def get(self, entity_id: uuid.UUID) -> Model | None:
        return self.db.get(self.model, entity_id)

    def first(self, *conditions: Any) -> Model | None:
        statement = select(self.model).where(*conditions).limit(1)
        return self.db.scalars(statement).first()

    def all(self, *conditions: Any, limit: int | None = None, offset: int = 0) -> Sequence[Model]:
        statement = select(self.model).where(*conditions)
        if offset:
            statement = statement.offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        return self.db.scalars(statement).all()

    def paginate(self, statement: Select, limit: int, offset: int) -> tuple[list[Any], int]:
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        total = self.db.scalar(count_statement) or 0
        rows = self.db.scalars(statement.limit(limit).offset(offset)).all()
        return list(rows), int(total)

    def count(self, *conditions: Any) -> int:
        statement = select(func.count(self.model.id)).where(*conditions)
        return int(self.db.scalar(statement) or 0)

    # ------------------------------------------------------------- writing
    def create(self, **values: Any) -> Model:
        entity = self.model(**values)
        self.db.add(entity)
        self.db.flush()
        return entity

    def add_all(self, entities: Sequence[Model]) -> None:
        self.db.add_all(list(entities))

    def update(self, entity: Model, **values: Any) -> Model:
        for key, value in values.items():
            if value is not None or key in _nullable_fields(entity):
                setattr(entity, key, value)
        self.db.flush()
        return entity

    def delete(self, entity: Model) -> None:
        self.db.delete(entity)
        self.db.flush()

    def flush(self) -> None:
        self.db.flush()


def _nullable_fields(entity: Any) -> set[str]:
    return {
        column.key
        for column in entity.__table__.columns
        if column.nullable and not column.default and not column.server_default
    }