"""Task, exam and grade schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import (
    ExamStatus,
    ExamType,
    GradeCategory,
    Priority,
    TaskStatus,
)
from app.schemas.common import ORMModel
from app.schemas.course import CourseSummary


class TaskBase(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    course_id: uuid.UUID | None = None
    priority: Priority = Priority.MEDIUM
    due_at: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=0, le=1440)


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    course_id: uuid.UUID | None = None
    priority: Priority | None = None
    status: TaskStatus | None = None
    due_at: datetime | None = None
    estimated_minutes: int | None = Field(default=None, ge=0, le=1440)
    position: int | None = Field(default=None, ge=0)


class TaskRead(ORMModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    course_id: uuid.UUID | None = None
    course: CourseSummary | None = None
    status: TaskStatus
    priority: Priority
    due_at: datetime | None = None
    completed_at: datetime | None = None
    estimated_minutes: int | None = None
    is_overdue: bool = False
    created_at: datetime
    updated_at: datetime


class TaskListFilters(BaseModel):
    status: TaskStatus | None = None
    priority: Priority | None = None
    course_id: uuid.UUID | None = None
    due_before: datetime | None = None
    due_after: datetime | None = None
    search: str | None = None


class ExamBase(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    course_id: uuid.UUID
    exam_type: ExamType = ExamType.PARTIAL
    scheduled_at: datetime
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    location: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=4000)
    weight: float | None = Field(default=None, ge=0, le=100)
    topics: str | None = Field(default=None, max_length=4000)


class ExamCreate(ExamBase):
    pass


class ExamUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    course_id: uuid.UUID | None = None
    exam_type: ExamType | None = None
    status: ExamStatus | None = None
    scheduled_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    location: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=4000)
    weight: float | None = Field(default=None, ge=0, le=100)
    topics: str | None = Field(default=None, max_length=4000)


class ExamRead(ORMModel):
    id: uuid.UUID
    title: str
    course_id: uuid.UUID
    course: CourseSummary | None = None
    exam_type: ExamType
    status: ExamStatus
    scheduled_at: datetime
    duration_minutes: int | None = None
    location: str | None = None
    notes: str | None = None
    weight: float | None = None
    topics: str | None = None
    days_until: int | None = None
    grade_id: uuid.UUID | None = None
    created_at: datetime


class GradeBase(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    course_id: uuid.UUID
    category: GradeCategory = GradeCategory.EXAM
    score: float = Field(ge=0)
    max_score: float = Field(default=100.0, gt=0)
    weight: float | None = Field(default=None, ge=0, le=100)
    graded_at: datetime | None = None
    graded_on_date: date | None = None
    exam_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class GradeCreate(GradeBase):
    pass


class GradeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    course_id: uuid.UUID | None = None
    category: GradeCategory | None = None
    score: float | None = Field(default=None, ge=0)
    max_score: float | None = Field(default=None, gt=0)
    weight: float | None = Field(default=None, ge=0, le=100)
    graded_at: datetime | None = None
    graded_on_date: date | None = None
    exam_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class GradeRead(ORMModel):
    id: uuid.UUID
    title: str
    course_id: uuid.UUID
    course: CourseSummary | None = None
    exam_id: uuid.UUID | None = None
    category: GradeCategory
    score: float
    max_score: float
    percentage: float
    weight: float | None = None
    graded_at: datetime | None = None
    graded_on_date: date | None = None
    notes: str | None = None
    created_at: datetime


class CourseGradeSummary(BaseModel):
    course_id: uuid.UUID
    course_name: str
    course_code: str
    color: str
    average: float
    highest: float
    lowest: float
    count: int
    projected: float | None = None
    required_to_pass: float | None = None
    trend: list[float] = []


class GradeOverview(BaseModel):
    overall_average: float | None = None
    courses: list[CourseGradeSummary]
    distribution: list[dict]
    category_breakdown: list[dict]
    recent: list[GradeRead]