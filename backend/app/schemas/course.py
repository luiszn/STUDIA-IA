"""Course and enrollment schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.enums import CourseStatus, EnrollmentRole
from app.schemas.common import ORMModel


class CourseBase(BaseModel):
    code: str = Field(min_length=2, max_length=32, examples=["REDES-101"])
    name: str = Field(min_length=2, max_length=160, examples=["Redes de Computadores"])
    description: str | None = Field(default=None, max_length=4000)
    professor: str | None = Field(default=None, max_length=120)
    credits: int = Field(default=3, ge=0, le=30)
    semester: str | None = Field(default=None, max_length=32, examples=["2026-1"])
    academic_year: str | None = Field(default=None, max_length=20)
    color: str = Field(default="#FF6B00", pattern=r"^#[0-9A-Fa-f]{6}$")

    @field_validator("code")
    @classmethod
    def _upper_code(cls, value: str) -> str:
        return value.strip().upper()


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=2, max_length=32)
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    professor: str | None = Field(default=None, max_length=120)
    credits: int | None = Field(default=None, ge=0, le=30)
    semester: str | None = Field(default=None, max_length=32)
    academic_year: str | None = Field(default=None, max_length=20)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    status: CourseStatus | None = None


class CourseSummary(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    professor: str | None = None
    color: str = "#FF6B00"
    credits: int = 3
    semester: str | None = None
    status: CourseStatus = CourseStatus.ACTIVE


class CourseRead(CourseSummary):
    description: str | None = None
    academic_year: str | None = None
    role: EnrollmentRole = EnrollmentRole.OWNER
    created_at: datetime
    updated_at: datetime

    task_count: int = 0
    pending_task_count: int = 0
    document_count: int = 0
    flashcard_count: int = 0
    exam_count: int = 0
    average_grade: float | None = None


class CourseStats(BaseModel):
    total_tasks: int
    completed_tasks: int
    overdue_tasks: int
    upcoming_exams: int
    average_grade: float | None = None
    highest_grade: float | None = None
    documents: int
    flashcards: int
    study_minutes: int