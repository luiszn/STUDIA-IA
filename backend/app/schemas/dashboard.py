"""Dashboard aggregation and global search schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import Priority
from app.schemas.study import RecommendationRead


class DashboardStats(BaseModel):
    active_courses: int
    total_courses: int
    pending_tasks: int
    overdue_tasks: int
    completed_tasks: int
    upcoming_exams: int
    next_exam_in_days: int | None = None
    average_grade: float | None = None
    study_minutes_week: int
    study_minutes_total: int
    documents: int
    flashcards: int
    flashcards_due: int
    study_streak_days: int
    daily_goal_minutes: int


class ActivityItem(BaseModel):
    id: str
    kind: Literal["task", "exam", "session"]
    title: str
    course_name: str | None = None
    course_code: str | None = None
    color: str | None = None
    date: datetime | None = None
    time_label: str | None = None
    priority: Priority | None = None
    status: str | None = None
    path: str
    is_overdue: bool = False


class PerformancePoint(BaseModel):
    label: str
    value: float


class PerformanceSeries(BaseModel):
    study_minutes: list[PerformancePoint]
    grades: list[PerformancePoint]
    by_course: list[dict]


class DashboardResponse(BaseModel):
    greeting: str
    generated_at: datetime
    stats: DashboardStats
    upcoming: list[ActivityItem]
    recommendation: RecommendationRead | None = None
    performance: PerformanceSeries
    focus_course: dict | None = None
    quick_actions: list[dict] = []


class CalendarEvent(BaseModel):
    id: str
    kind: Literal["task", "exam", "session", "plan"]
    title: str
    course_name: str | None = None
    color: str | None = None
    date: date
    time: str | None = None
    priority: Priority | None = None
    status: str | None = None
    path: str
    meta: dict = {}


class CalendarResponse(BaseModel):
    start: date
    end: date
    events: list[CalendarEvent]


class SearchResultItem(BaseModel):
    id: uuid.UUID | str
    type: Literal["course", "task", "document", "flashcard", "conversation", "exam", "grade"]
    title: str
    subtitle: str | None = None
    path: str
    meta: dict = {}


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResultItem]
    groups: dict[str, int] = Field(default_factory=dict)