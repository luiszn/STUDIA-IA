"""AI request/response schemas for the STUDIA AI endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import Difficulty, QuestionType, StudyLevel
from app.schemas.common import ORMModel
from app.schemas.document import SourceCitation


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: uuid.UUID | None = Field(
        default=None, description="Omit to start a new conversation."
    )
    course_id: uuid.UUID | None = Field(default=None, description="Course context")
    document_ids: list[uuid.UUID] = Field(
        default_factory=list,
        max_length=20,
        description="Restrict retrieval to these documents. Empty = all your documents.",
    )
    use_rag: bool = Field(default=True, description="Ground the answer in your documents.")
    temperature: float | None = Field(default=None, ge=0.0, le=1.5)


class SourceRead(SourceCitation):
    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    title: str
    message: str
    sources: list[SourceCitation] = []
    used_rag: bool
    provider: str
    model: str
    latency_ms: int
    created_at: datetime


class MessageRead(ORMModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    sources: list[dict] | None = None
    provider: str | None = None
    model: str | None = None
    latency_ms: int | None = None
    created_at: datetime


class ConversationRead(ORMModel):
    id: uuid.UUID
    title: str
    course_id: uuid.UUID | None = None
    course_name: str | None = None
    provider: str | None = None
    model: str | None = None
    message_count: int
    used_rag: bool
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None = None


class ConversationDetail(ConversationRead):
    messages: list[MessageRead] = []


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)


class ExplainTopicRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=300)
    course_id: uuid.UUID | None = None
    document_ids: list[uuid.UUID] = []
    level: StudyLevel = StudyLevel.BEGINNER
    use_rag: bool = True


class ExplainResult(BaseModel):
    topic: str
    level: StudyLevel
    answer: str
    sources: list[SourceCitation] = []
    used_rag: bool
    provider: str
    model: str


class QuestionOption(BaseModel):
    id: str = Field(min_length=1, max_length=4)
    text: str = Field(min_length=1, max_length=600)


class GeneratedQuestion(BaseModel):
    id: str
    type: QuestionType
    prompt: str
    options: list[QuestionOption] = []
    correct_answer: str = Field(description="Option id for MCQ/TF, otherwise the answer text")
    correct_option_id: str | None = None
    explanation: str = ""
    difficulty: Difficulty = Difficulty.MEDIUM
    topic: str | None = None
    source_document_id: uuid.UUID | None = None


class GenerateQuestionsRequest(BaseModel):
    document_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)
    course_id: uuid.UUID | None = None
    count: int = Field(default=8, ge=1, le=40)
    question_types: list[QuestionType] = Field(
        default_factory=lambda: [QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]
    )
    difficulty: Difficulty = Difficulty.MEDIUM
    topics: list[str] = Field(default_factory=list, max_length=20)
    use_rag: bool = True


class GenerateQuestionsResult(BaseModel):
    questions: list[GeneratedQuestion]
    provider: str
    model: str
    sources: list[SourceCitation] = []
    count: int


class AnswerPayload(BaseModel):
    question_id: str
    answer: str = Field(max_length=2000)


class GradeAnswersRequest(BaseModel):
    questions: list[AnswerPayload] = Field(min_length=1, max_length=60)


class GradeQuestionsRequest(BaseModel):
    """Round trip: the quiz the student just took."""

    questions: list[GeneratedQuestion] = Field(min_length=1, max_length=60)
    answers: list[AnswerPayload] = Field(min_length=1, max_length=60)


class GradedAnswer(BaseModel):
    question_id: str
    is_correct: bool
    expected_answer: str
    explanation: str = ""
    awarded_points: float = 0.0
    max_points: float = 1.0


class GradeAnswersResult(BaseModel):
    score: float = Field(description="Percentage 0-100")
    correct_count: int
    total: int
    answers: list[GradedAnswer]
    feedback: str = ""


class AIProviderStatus(BaseModel):
    provider: str
    available: bool
    model: str | None = None
    embedding_model: str | None = None
    message: str
    latency_ms: int | None = None