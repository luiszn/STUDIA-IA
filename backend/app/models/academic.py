"""Academic work models: tasks, exams and grades."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UTCDateTime, Uuid, created_at_column, updated_at_column
from app.models.course import enum_column
from app.models.enums import (
    ExamStatus,
    ExamType,
    GradeCategory,
    Priority,
    TaskStatus,
)

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.user import User


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = enum_column(TaskStatus, TaskStatus.PENDING)
    priority: Mapped[str] = enum_column(Priority, Priority.MEDIUM)
    due_at: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    user: Mapped[User] = relationship(back_populates="tasks")
    course: Mapped[Course | None] = relationship(back_populates="tasks", lazy="joined")

    def is_overdue(self, now: datetime | None = None) -> bool:
        if self.status == TaskStatus.COMPLETED or self.due_at is None:
            return False
        due = self.due_at
        now = now or datetime.now(due.tzinfo or None)
        if due.tzinfo is None and now.tzinfo is not None:
            due = due.replace(tzinfo=now.tzinfo)
        return due < now


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    exam_type: Mapped[str] = enum_column(ExamType, ExamType.PARTIAL)
    status: Mapped[str] = enum_column(ExamStatus, ExamStatus.SCHEDULED)
    scheduled_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, index=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    location: Mapped[str | None] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(Text)
    weight: Mapped[float | None] = mapped_column(Float)
    topics: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    user: Mapped[User] = relationship(back_populates="exams")
    course: Mapped[Course] = relationship(back_populates="exams", lazy="joined")
    grades: Mapped[list[Grade]] = relationship(back_populates="exam")


class Grade(Base):
    __tablename__ = "grades"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    exam_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("exams.id", ondelete="SET NULL"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = enum_column(GradeCategory, GradeCategory.EXAM)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    weight: Mapped[float | None] = mapped_column(Float)
    graded_at: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
    graded_on_date: Mapped[datetime | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    is_projection: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    user: Mapped[User] = relationship(back_populates="grades")
    course: Mapped[Course] = relationship(back_populates="grades", lazy="joined")
    exam: Mapped[Exam | None] = relationship(back_populates="grades", lazy="joined")

    @property
    def percentage(self) -> float:
        if not self.max_score:
            return 0.0
        return round((self.score / self.max_score) * 100, 2)
