"""Document and ingestion schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import DocumentStatus, SummaryStyle
from app.schemas.common import ORMModel
from app.schemas.course import CourseSummary


class DocumentRead(ORMModel):
    id: uuid.UUID
    title: str
    filename: str
    content_type: str
    extension: str
    size_bytes: int
    page_count: int
    word_count: int
    char_count: int
    chunk_count: int
    status: DocumentStatus
    error_message: str | None = None
    detected_language: str | None = None
    summary: str | None = None
    topics: list[str] | None = None
    course_id: uuid.UUID | None = None
    course: CourseSummary | None = None
    created_at: datetime
    updated_at: datetime


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    course_id: uuid.UUID | None = None


class DocumentChunkRead(ORMModel):
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    page_number: int | None = None
    heading: str | None = None
    token_estimate: int


class DocumentDetail(DocumentRead):
    preview: str | None = None
    chunks: list[DocumentChunkRead] = []


class SummaryRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(min_length=1, max_length=10)
    style: SummaryStyle = SummaryStyle.SHORT
    course_id: uuid.UUID | None = None
    focus: str | None = Field(default=None, max_length=500, description="Optional topic focus")


class SummaryResult(BaseModel):
    summary: str
    style: SummaryStyle
    sources: list[SourceCitation] = []
    provider: str
    model: str
    tokens: int | None = None


class SourceCitation(BaseModel):
    document_id: uuid.UUID
    title: str
    filename: str
    chunk_index: int | None = None
    page_number: int | None = None
    score: float | None = None
    excerpt: str | None = None


SummaryResult.model_rebuild()