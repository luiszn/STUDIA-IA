"""Document ingestion models: source files and their vector chunks."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Uuid, created_at_column, updated_at_column
from app.models.course import enum_column
from app.models.enums import DocumentStatus

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.user import User


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    extension: Mapped[str] = mapped_column(String(10), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = enum_column(DocumentStatus, DocumentStatus.UPLOADED)
    error_message: Mapped[str | None] = mapped_column(Text)
    detected_language: Mapped[str | None] = mapped_column(String(16))
    summary: Mapped[str | None] = mapped_column(Text)
    topics: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    user: Mapped[User] = relationship(back_populates="documents")
    course: Mapped[Course | None] = relationship(back_populates="documents", lazy="joined")
    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def is_ready(self) -> bool:
        return self.status == DocumentStatus.READY


class DocumentChunk(Base):
    """A retrievable slice of a document with its embedding vector.

    `embedding` is stored as JSON so the exact same table works on PostgreSQL
    (a `pgvector` column can be swapped in without touching the app layer) and
    on SQLite for local development.
    """

    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_doc_idx", "document_id", "chunk_index"),
        Index("ix_document_chunks_user_idx", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, default=0)
    char_end: Mapped[int] = mapped_column(Integer, default=0)
    page_number: Mapped[int | None] = mapped_column(Integer)
    heading: Mapped[str | None] = mapped_column(String(255))
    token_estimate: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[list | None] = mapped_column(JSON)
    embedding_model: Mapped[str | None] = mapped_column(String(120))
    embedding_score_hint: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = created_at_column()

    document: Mapped[Document] = relationship(back_populates="chunks")

    @property
    def citation_label(self) -> str:
        if self.page_number:
            return f"p. {self.page_number}"
        return ""
