"""User account and authentication support models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, Uuid, created_at_column, updated_at_column, utcnow

if TYPE_CHECKING:
    from app.models.academic import Exam, Grade, Task
    from app.models.course import Course, Enrollment
    from app.models.document import Document
    from app.models.study import (
        Conversation,
        Flashcard,
        Recommendation,
        StudyPlan,
        StudySession,
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    university: Mapped[str | None] = mapped_column(String(160))
    career: Mapped[str | None] = mapped_column(String(160))
    academic_year: Mapped[str | None] = mapped_column(String(40))
    timezone: Mapped[str] = mapped_column(String(64), default="America/Bogota")
    daily_study_goal_minutes: Mapped[int] = mapped_column(Integer, default=120)
    locale: Mapped[str] = mapped_column(String(10), default="es")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    enrollments: Mapped[list[Enrollment]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    courses: Mapped[list[Course]] = relationship(
        secondary="enrollments",
        viewonly=True,
    )
    tasks: Mapped[list[Task]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    exams: Mapped[list[Exam]] = relationship(back_populates="user", cascade="all, delete-orphan")
    grades: Mapped[list[Grade]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    flashcards: Mapped[list[Flashcard]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    study_plans: Mapped[list[StudyPlan]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    study_sessions: Mapped[list[StudySession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list[Recommendation]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def initials(self) -> str:
        parts = [part for part in self.full_name.split() if part]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return f"{parts[0][0]}{parts[-1][0]}".upper()

    def touch_login(self) -> None:
        self.last_login_at = utcnow()


class PasswordResetToken(Base):
    """One-time password reset token.

    The creation/consumption flow is implemented (`services/auth_service.py`) so
    the feature only needs an email transport to go live.
    """

    __tablename__ = "password_reset_tokens"
    __table_args__ = (UniqueConstraint("token", name="uq_password_reset_tokens_token"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = created_at_column()

    user: Mapped[User] = relationship(back_populates="reset_tokens")

    @property
    def is_usable(self) -> bool:
        from datetime import UTC

        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return self.used_at is None and expires > datetime.now(UTC)
