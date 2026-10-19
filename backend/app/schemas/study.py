"""Flashcards, study plans, sessions and recommendation schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import (
    FlashcardDifficulty,
    FlashcardOrigin,
    FlashcardStatus,
    Priority,
    RecommendationKind,
    StudyLevel,
    StudyPlanStatus,
)
from app.schemas.common import ORMModel
from app.schemas.course import CourseSummary


class FlashcardBase(BaseModel):
    front: str = Field(min_length=1, max_length=1000)
    back: str = Field(min_length=1, max_length=2000)
    explanation: str | None = Field(default=None, max_length=2000)
    deck: str = Field(default="General", min_length=1, max_length=120)
    course_id: uuid.UUID | None = None
    difficulty: FlashcardDifficulty = FlashcardDifficulty.MEDIUM
    tags: list[str] = []


class FlashcardCreate(FlashcardBase):
    source_document_id: uuid.UUID | None = None
    origin: FlashcardOrigin = FlashcardOrigin.MANUAL


class FlashcardUpdate(BaseModel):
    front: str | None = Field(default=None, min_length=1, max_length=1000)
    back: str | None = Field(default=None, min_length=1, max_length=2000)
    explanation: str | None = Field(default=None, max_length=2000)
    deck: str | None = Field(default=None, min_length=1, max_length=120)
    course_id: uuid.UUID | None = None
    difficulty: FlashcardDifficulty | None = None
    status: FlashcardStatus | None = None


class FlashcardRead(ORMModel):
    id: uuid.UUID
    front: str
    back: str
    explanation: str | None = None
    deck: str
    course_id: uuid.UUID | None = None
    course: CourseSummary | None = None
    origin: FlashcardOrigin
    difficulty: FlashcardDifficulty
    status: FlashcardStatus
    tags: list[str] = []
    source_document_id: uuid.UUID | None = None
    repetitions: int
    lapses: int
    ease_factor: float
    interval_days: int
    next_review_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    created_at: datetime


class FlashcardDeckSummary(BaseModel):
    name: str
    course_id: uuid.UUID | None = None
    course_name: str | None = None
    color: str | None = None
    total: int
    new: int
    due_today: int
    mastered: int
    average_difficulty: float


class FlashcardReviewRequest(BaseModel):
    card_id: uuid.UUID
    quality: int = Field(ge=0, le=5, description="SM-2 quality: 0-5")
    response_seconds: int | None = Field(default=None, ge=0, le=7200)


class FlashcardReviewResult(BaseModel):
    card_id: uuid.UUID
    status: FlashcardStatus
    repetitions: int
    interval_days: int
    next_review_at: datetime | None = None
    message: str


class GenerateFlashcardsRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(min_length=1, max_length=10)
    count: int = Field(default=12, ge=1, le=60)
    deck: str = Field(default="General", min_length=1, max_length=120)
    course_id: uuid.UUID | None = None
    difficulty: FlashcardDifficulty = FlashcardDifficulty.MEDIUM
    save: bool = True
    focus: str | None = Field(default=None, max_length=500)


class GenerateFlashcardsResult(BaseModel):
    flashcards: list[FlashcardRead]
    created: int
    sources: list = []
    provider: str
    model: str


class StudyPlanCreate(BaseModel):
    course_id: uuid.UUID | None = None
    exam_id: uuid.UUID | None = None
    title: str | None = Field(default=None, max_length=180)
    exam_date: datetime | None = None
    level: StudyLevel = StudyLevel.INTERMEDIATE
    daily_minutes: int = Field(default=120, ge=15, le=720)
    total_days: int = Field(default=7, ge=1, le=90)
    focus_topics: list[str] = []
    document_ids: list[uuid.UUID] = []
    use_weak_topics: bool = True


class StudyPlanDay(BaseModel):
    day: int
    date: str | None = None
    title: str
    focus: str
    theory_minutes: int = 0
    practice_minutes: int = 0
    review_minutes: int = 0
    objectives: list[str] = []
    resources: list[str] = []


class StudyPlanRead(ORMModel):
    id: uuid.UUID
    title: str
    course_id: uuid.UUID | None = None
    course: CourseSummary | None = None
    exam_id: uuid.UUID | None = None
    exam_date: datetime | None = None
    level: StudyLevel
    daily_minutes: int
    total_days: int
    total_minutes: int
    status: StudyPlanStatus
    days: list[StudyPlanDay] = []
    weak_topics: list[str] = []
    rationale: str | None = None
    provider: str | None = None
    model: str | None = None
    created_at: datetime


class StudyPlanConvertRequest(BaseModel):
    """Turns a plan into real tasks + calendar study sessions."""

    start_date: datetime | None = None
    create_tasks: bool = True
    create_sessions: bool = True


class StudySessionCreate(BaseModel):
    focus: str = Field(min_length=2, max_length=160)
    course_id: uuid.UUID | None = None
    study_plan_id: uuid.UUID | None = None
    started_at: datetime | None = None
    duration_minutes: int = Field(default=60, ge=1, le=1440)
    notes: str | None = Field(default=None, max_length=2000)


class StudySessionRead(ORMModel):
    id: uuid.UUID
    focus: str
    course_id: uuid.UUID | None = None
    course: CourseSummary | None = None
    study_plan_id: uuid.UUID | None = None
    started_at: datetime
    ended_at: datetime | None = None
    duration_minutes: int
    notes: str | None = None


class RecommendationRead(ORMModel):
    id: uuid.UUID
    kind: RecommendationKind
    title: str
    message: str
    priority: Priority
    score: float
    cta_label: str | None = None
    cta_path: str | None = None
    evidence: dict | None = None
    course_id: uuid.UUID | None = None
    course: CourseSummary | None = None
    is_read: bool
    is_dismissed: bool
    created_at: datetime
    expires_at: datetime | None = None


class WeakTopic(BaseModel):
    topic: str
    course_id: uuid.UUID | None = None
    course_name: str | None = None
    confidence: float
    evidence: list[str] = []
    suggested_action: str | None = None


class RecommendationUpdate(BaseModel):
    is_read: bool = False
    is_dismissed: bool = False