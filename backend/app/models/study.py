"""AI / study models: conversations, flashcards, plans, sessions, recommendations."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, Uuid, created_at_column, updated_at_column
from app.models.course import enum_column
from app.models.enums import (
    FlashcardDifficulty,
    FlashcardOrigin,
    FlashcardStatus,
    MessageRole,
    Priority,
    RecommendationKind,
    StudyLevel,
    StudyPlanStatus,
)

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.user import User


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(120))
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    used_rag: Mapped[bool] = mapped_column(Boolean, default=False)
    last_message_at: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    user: Mapped[User] = relationship(back_populates="conversations")
    course: Mapped[Course | None] = relationship(lazy="joined")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="selectin",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    role: Mapped[str] = enum_column(MessageRole, MessageRole.USER)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list | None] = mapped_column(JSON)
    provider: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(120))
    tokens_prompt: Mapped[int | None] = mapped_column(Integer)
    tokens_completion: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = created_at_column()

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Flashcard(Base):
    """Spaced-repetition ready: SM-2 fields are stored up front."""

    __tablename__ = "flashcards"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    deck: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    front: Mapped[str] = mapped_column(Text, nullable=False)
    back: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str] = enum_column(FlashcardOrigin, FlashcardOrigin.MANUAL)
    difficulty: Mapped[str] = enum_column(FlashcardDifficulty, FlashcardDifficulty.MEDIUM)
    status: Mapped[str] = enum_column(FlashcardStatus, FlashcardStatus.NEW)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    next_review_at: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    user: Mapped[User] = relationship(back_populates="flashcards")
    course: Mapped[Course | None] = relationship(back_populates="flashcards", lazy="joined")


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    exam_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("exams.id", ondelete="SET NULL")
    )
    exam_date: Mapped[datetime | None] = mapped_column(UTCDateTime)
    level: Mapped[str] = enum_column(StudyLevel, StudyLevel.INTERMEDIATE)
    daily_minutes: Mapped[int] = mapped_column(Integer, default=120)
    total_days: Mapped[int] = mapped_column(Integer, default=7)
    total_minutes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = enum_column(StudyPlanStatus, StudyPlanStatus.DRAFT)
    days: Mapped[list | None] = mapped_column(JSON)
    weak_topics: Mapped[list | None] = mapped_column(JSON)
    rationale: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    user: Mapped[User] = relationship(back_populates="study_plans")
    course: Mapped[Course | None] = relationship(back_populates="study_plans", lazy="joined")


class StudySession(Base):
    __tablename__ = "study_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"), index=True
    )
    study_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("study_plans.id", ondelete="SET NULL")
    )
    focus: Mapped[str] = mapped_column(String(160), nullable=False)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()

    user: Mapped[User] = relationship(back_populates="study_sessions")
    course: Mapped[Course | None] = relationship(lazy="joined")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = enum_column(RecommendationKind, RecommendationKind.PRIORITY_TASK)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = enum_column(Priority, Priority.MEDIUM)
    score: Mapped[float] = mapped_column(Float, default=0.5)
    cta_label: Mapped[str | None] = mapped_column(String(80))
    cta_path: Mapped[str | None] = mapped_column(String(255))
    evidence: Mapped[dict | None] = mapped_column(JSON)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = created_at_column()
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)

    user: Mapped[User] = relationship(back_populates="recommendations")
    course: Mapped[Course | None] = relationship(lazy="joined")
