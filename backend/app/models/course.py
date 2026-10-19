"""Course and enrollment models.

Access to a course is derived from `Enrollment` (never duplicated on the
course row), so the schema supports shared courses later without a migration.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Uuid, created_at_column, updated_at_column
from app.models.enums import CourseStatus, EnrollmentRole, EnrollmentStatus

if TYPE_CHECKING:
    from app.models.academic import Exam, Grade, Task
    from app.models.document import Document
    from app.models.study import Flashcard, StudyPlan
    from app.models.user import User


def enum_column(enum_cls: type, default: str | None = None) -> Mapped[str]:
    return mapped_column(
        SAEnum(enum_cls, native_enum=False, length=32, validate_strings=True),
        default=default,
        nullable=False,
        index=True,
    )


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    professor: Mapped[str | None] = mapped_column(String(120))
    credits: Mapped[int] = mapped_column(Integer, default=3)
    semester: Mapped[str | None] = mapped_column(String(32), index=True)
    academic_year: Mapped[str | None] = mapped_column(String(20))
    color: Mapped[str] = mapped_column(String(9), default="#FF6B00")
    status: Mapped[str] = enum_column(CourseStatus, CourseStatus.ACTIVE)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    members: Mapped[list[Enrollment]] = relationship(
        back_populates="course", cascade="all, delete-orphan", lazy="selectin"
    )
    tasks: Mapped[list[Task]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    exams: Mapped[list[Exam]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    grades: Mapped[list[Grade]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    documents: Mapped[list[Document]] = relationship(back_populates="course")
    flashcards: Mapped[list[Flashcard]] = relationship(back_populates="course")
    study_plans: Mapped[list[StudyPlan]] = relationship(back_populates="course")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("user_id", "course_id", name="uq_enrollments_user_course"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = enum_column(EnrollmentRole, EnrollmentRole.OWNER)
    status: Mapped[str] = enum_column(EnrollmentStatus, EnrollmentStatus.ACTIVE)
    is_pinned: Mapped[bool] = mapped_column(default=False)
    joined_at: Mapped[datetime] = created_at_column()

    user: Mapped[User] = relationship(back_populates="enrollments")
    course: Mapped[Course] = relationship(
        back_populates="members",
        foreign_keys=[course_id],
        lazy="selectin",
    )

    @property
    def is_owner(self) -> bool:
        return self.role == EnrollmentRole.OWNER