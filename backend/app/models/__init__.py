"""Model registry — every model is imported here so Alembic autogenerate and
`Base.metadata.create_all` see the complete schema."""

from app.db.base import Base
from app.models.academic import Exam, Grade, Task
from app.models.course import Course, Enrollment
from app.models.document import Document, DocumentChunk
from app.models.enums import (
    CourseStatus,
    Difficulty,
    DocumentStatus,
    EnrollmentRole,
    EnrollmentStatus,
    ExamStatus,
    ExamType,
    FlashcardDifficulty,
    FlashcardOrigin,
    FlashcardStatus,
    GradeCategory,
    MessageRole,
    Priority,
    QuestionType,
    RecommendationKind,
    StudyLevel,
    StudyPlanStatus,
    SummaryStyle,
    TaskStatus,
)
from app.models.study import (
    Conversation,
    Flashcard,
    Message,
    Recommendation,
    StudyPlan,
    StudySession,
)
from app.models.user import PasswordResetToken, User

__all__ = [
    "Base",
    "Course",
    "CourseStatus",
    "Conversation",
    "Difficulty",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "Enrollment",
    "EnrollmentRole",
    "EnrollmentStatus",
    "Exam",
    "ExamStatus",
    "ExamType",
    "Flashcard",
    "FlashcardDifficulty",
    "FlashcardOrigin",
    "FlashcardStatus",
    "Grade",
    "GradeCategory",
    "Message",
    "MessageRole",
    "PasswordResetToken",
    "Priority",
    "QuestionType",
    "Recommendation",
    "RecommendationKind",
    "StudyLevel",
    "StudyPlan",
    "StudyPlanStatus",
    "StudySession",
    "SummaryStyle",
    "Task",
    "TaskStatus",
    "User",
]