"""Domain enumerations shared by models, schemas and the frontend contract.

Stored as `VARCHAR` + `CHECK` constraint (`native_enum=False`) so the schema is
identical on PostgreSQL and SQLite and Alembic autogenerate stays portable.
"""

from __future__ import annotations

from enum import StrEnum


class CourseStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class EnrollmentRole(StrEnum):
    OWNER = "owner"
    COLLABORATOR = "collaborator"
    VIEWER = "viewer"


class EnrollmentStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"  # derived, never persisted by the write paths


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ExamType(StrEnum):
    QUIZ = "quiz"
    MIDTERM = "midterm"
    PARTIAL = "partial"
    FINAL = "final"
    PROJECT = "project"
    OTHER = "other"


class ExamStatus(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class GradeCategory(StrEnum):
    EXAM = "exam"
    QUIZ = "quiz"
    PRACTICE = "practice"
    LAB = "lab"
    ASSIGNMENT = "assignment"
    PROJECT = "project"
    OTHER = "other"


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class FlashcardOrigin(StrEnum):
    MANUAL = "manual"
    AI = "ai"


class FlashcardDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class FlashcardStatus(StrEnum):
    NEW = "new"
    LEARNING = "learning"
    REVIEW = "review"
    MASTERED = "mastered"


class StudyLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class StudyPlanStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"


class RecommendationKind(StrEnum):
    UPCOMING_EXAM = "upcoming_exam"
    PRIORITY_TASK = "priority_task"
    WEAK_TOPIC = "weak_topic"
    DOCUMENT_INSIGHT = "document_insight"
    WORKLOAD_BALANCE = "workload_balance"
    STUDY_HABIT = "study_habit"


class SummaryStyle(StrEnum):
    SHORT = "short"
    DETAILED = "detailed"
    EXAM = "exam"
    KEY_POINTS = "key_points"


class QuestionType(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class AIProviderName(StrEnum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    LOCAL = "local"