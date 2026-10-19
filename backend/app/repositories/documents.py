"""Document repository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, func, select

from app.models.document import Document, DocumentChunk
from app.models.enums import DocumentStatus
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    model = Document

    def query_for_user(self, user_id: uuid.UUID) -> Select:
        return select(Document).where(Document.user_id == user_id)

    def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        course_id: uuid.UUID | None = None,
        status: DocumentStatus | None = None,
        search: str | None = None,
    ) -> Sequence[Document]:
        statement = self.query_for_user(user_id)
        if course_id is not None:
            statement = statement.where(Document.course_id == course_id)
        if status is not None:
            statement = statement.where(Document.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(Document.title.ilike(pattern))
        return self.db.scalars(statement.order_by(Document.created_at.desc())).all()

    def get_owned(self, user_id: uuid.UUID, document_id: uuid.UUID) -> Document | None:
        return self.db.scalars(
            select(Document).where(Document.id == document_id, Document.user_id == user_id)
        ).first()

    def get_many_owned(
        self, user_id: uuid.UUID, document_ids: list[uuid.UUID]
    ) -> list[Document]:
        if not document_ids:
            return []
        return list(
            self.db.scalars(
                select(Document).where(
                    Document.user_id == user_id, Document.id.in_(document_ids)
                )
            ).all()
        )

    def chunk_count(self, document_id: uuid.UUID) -> int:
        return int(
            self.db.scalar(
                select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == document_id)
            )
            or 0
        )

    def chunks(self, document_id: uuid.UUID, *, limit: int = 50) -> Sequence[DocumentChunk]:
        return self.db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .limit(limit)
        ).all()

    def delete_owned(self, user_id: uuid.UUID, document_id: uuid.UUID) -> Document | None:
        document = self.get_owned(user_id, document_id)
        if document is None:
            return None
        self.db.delete(document)
        self.db.flush()
        return document