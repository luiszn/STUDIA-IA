"""STUDIA AI endpoints: chat, RAG generation, study plans and provider status."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.ai.registry import get_ai_provider, get_health
from app.api.deps import CurrentUser, DbSession
from app.schemas.ai import (
    AIProviderStatus,
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationRead,
    ConversationUpdate,
    ExplainResult,
    ExplainTopicRequest,
    GenerateQuestionsRequest,
    GenerateQuestionsResult,
    GradeAnswersRequest,
    GradeAnswersResult,
    GradeQuestionsRequest,
)
from app.schemas.common import MessageResponse
from app.schemas.document import SummaryRequest, SummaryResult
from app.schemas.study import (
    GenerateFlashcardsRequest,
    GenerateFlashcardsResult,
    StudyPlanConvertRequest,
    StudyPlanCreate,
    StudyPlanRead,
    WeakTopic,
)
from app.services.ai_chat_service import ChatService
from app.services.ai_generator_service import GeneratorService
from app.services.ai_plan_service import StudyPlanService
from app.services.insight_service import InsightService
from app.services.study_service import StudyService

router = APIRouter(prefix="/ai", tags=["studia-ai"])


# ------------------------------------------------------------------- chat
@router.post("/chat", response_model=ChatResponse, summary="Chat with STUDIA AI (RAG grounded)")
async def chat(payload: ChatRequest, user: CurrentUser, db: DbSession) -> ChatResponse:
    return await ChatService(db, user).send(payload)


@router.get("/conversations", response_model=list[ConversationRead], summary="List conversations")
def list_conversations(user: CurrentUser, db: DbSession) -> list[ConversationRead]:
    return ChatService(db, user).list_conversations()


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    summary="Conversation with its messages",
)
def get_conversation(
    conversation_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> ConversationDetail:
    return ChatService(db, user).get_conversation(conversation_id)


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationRead,
    summary="Rename a conversation",
)
def rename_conversation(
    conversation_id: uuid.UUID, payload: ConversationUpdate, user: CurrentUser, db: DbSession
) -> ConversationRead:
    return ChatService(db, user).rename_conversation(conversation_id, payload.title or "Conversación")


@router.delete(
    "/conversations/{conversation_id}",
    response_model=MessageResponse,
    summary="Delete a conversation",
)
def delete_conversation(
    conversation_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> MessageResponse:
    ChatService(db, user).delete_conversation(conversation_id)
    return MessageResponse(message="Conversation deleted.")


# -------------------------------------------------------------- generators
@router.post("/summarize", response_model=SummaryResult, summary="Summarize documents")
async def summarize(payload: SummaryRequest, user: CurrentUser, db: DbSession) -> SummaryResult:
    return await GeneratorService(db, user).summarize(payload)


@router.post(
    "/questions", response_model=GenerateQuestionsResult, summary="Generate exam questions"
)
async def questions(
    payload: GenerateQuestionsRequest, user: CurrentUser, db: DbSession
) -> GenerateQuestionsResult:
    return await GeneratorService(db, user).questions(payload)


@router.post(
    "/questions/grade",
    response_model=GradeAnswersResult,
    summary="Grade a set of generated answers",
)
def grade_answers(
    payload: GradeQuestionsRequest, user: CurrentUser, db: DbSession
) -> GradeAnswersResult:
    return GeneratorService(db, user).grade_answers(payload.questions, GradeAnswersRequest(questions=payload.answers))


@router.post(
    "/flashcards",
    response_model=GenerateFlashcardsResult,
    summary="Generate and store flashcards from documents",
)
async def flashcards(
    payload: GenerateFlashcardsRequest, user: CurrentUser, db: DbSession
) -> GenerateFlashcardsResult:
    return await GeneratorService(db, user).flashcards(payload)


@router.post("/explain", response_model=ExplainResult, summary="Explain a topic with course context")
async def explain(payload: ExplainTopicRequest, user: CurrentUser, db: DbSession) -> ExplainResult:
    return await GeneratorService(db, user).explain(
        topic=payload.topic,
        course_id=payload.course_id,
        level=payload.level,
        document_ids=payload.document_ids,
        use_rag=payload.use_rag,
    )


# -------------------------------------------------------------- study plan
@router.get("/study-plans", response_model=list[StudyPlanRead], summary="List study plans")
def list_study_plans(user: CurrentUser, db: DbSession) -> list[StudyPlanRead]:
    return StudyService(db, user).list_plans()


@router.post(
    "/study-plans",
    response_model=StudyPlanRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an AI study plan",
)
async def create_study_plan(
    payload: StudyPlanCreate, user: CurrentUser, db: DbSession
) -> StudyPlanRead:
    return await StudyPlanService(db, user).generate(payload)


@router.get("/study-plans/{plan_id}", response_model=StudyPlanRead, summary="Get one study plan")
def get_study_plan(plan_id: uuid.UUID, user: CurrentUser, db: DbSession) -> StudyPlanRead:
    return StudyService(db, user).get_plan(plan_id)


@router.post(
    "/study-plans/{plan_id}/convert",
    summary="Turn a study plan into tasks and calendar sessions",
)
def convert_study_plan(
    plan_id: uuid.UUID, payload: StudyPlanConvertRequest, user: CurrentUser, db: DbSession
) -> dict:
    return StudyService(db, user).convert_plan(plan_id, payload)


@router.delete("/study-plans/{plan_id}", response_model=MessageResponse, summary="Delete a plan")
def delete_study_plan(plan_id: uuid.UUID, user: CurrentUser, db: DbSession) -> MessageResponse:
    StudyService(db, user).delete_plan(plan_id)
    return MessageResponse(message="Study plan deleted.")


# --------------------------------------------------------------- insights
@router.get("/weak-topics", response_model=list[WeakTopic], summary="Detected weak topics")
async def weak_topics(user: CurrentUser, db: DbSession) -> list[WeakTopic]:
    return await InsightService(db, user).weak_topics()


@router.get("/status", response_model=AIProviderStatus, summary="AI provider readiness")
async def ai_status(
    user: CurrentUser,
    refresh: bool = Query(default=False, description="Bypass the cache"),
) -> AIProviderStatus:
    health = await get_health(force=refresh)
    provider = get_ai_provider()
    return AIProviderStatus(
        provider=health.provider,
        available=health.available,
        model=health.model or provider.model_name,
        embedding_model=health.embedding_model or provider.embedding_model_name,
        message=health.message,
        latency_ms=health.latency_ms,
    )