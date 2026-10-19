"""STUDIA AI chat service — RAG grounded academic conversation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.ai.base import ChatMessage
from app.ai.prompts import (
    academic_system_prompt,
    build_student_context,
    conversation_title_prompt,
    rag_block,
)
from app.ai.rag.retriever import Retriever
from app.ai.registry import resolve_provider
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.models.enums import MessageRole
from app.models.study import Conversation
from app.models.user import User
from app.repositories.study import ConversationRepository
from app.schemas.ai import ChatRequest, ChatResponse, ConversationDetail, ConversationRead
from app.schemas.document import SourceCitation
from app.services.academic_service import GradeService
from app.services.course_service import CourseService
from app.services.study_service import StudyService
from app.utils.text import excerpt

logger = get_logger("app.ai.chat")

_HISTORY_LIMIT = 12
_TITLE_MAX = 60


class ChatService:
    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user
        self.conversations = ConversationRepository(db)

    async def send(self, payload: ChatRequest) -> ChatResponse:
        resolved = await resolve_provider()
        provider = resolved.provider

        conversation = self._conversation(payload)
        history = self.conversations.recent_messages(conversation.id, limit=_HISTORY_LIMIT)
        self.conversations.add_message(
            conversation,
            role=MessageRole.USER,
            content=payload.message,
            provider=provider.name,
        )

        context_block = ""
        sources: list = []
        used_rag = False
        if payload.use_rag:
            retriever = Retriever(self.db, provider, self.user.id)
            context = await retriever.retrieve(
                payload.message, document_ids=payload.document_ids or None
            )
            used_rag = context.used_rag
            # `mode="json"` keeps the citation JSON-serialisable (uuids become
            # strings) so it can be stored in the messages row and returned.
            sources = [source.model_dump(mode="json") for source in context.sources]
            if context.context_text:
                context_block = rag_block(context.context_text)
                conversation.used_rag = True

        messages = [
            *[
                ChatMessage(role=message.role, content=message.content)
                for message in history
            ],
            ChatMessage.user(
                f"{self._student_context()}\n\n{context_block}\n\n{payload.message}".strip()
            ),
        ]

        completion = await provider.complete(
            messages,
            system=academic_system_prompt(),
            temperature=payload.temperature,
        )
        answer = self._decorate(completion.content, used_rag=used_rag, fallback=resolved.used_fallback)

        message = self.conversations.add_message(
            conversation,
            role=MessageRole.ASSISTANT,
            content=answer,
            sources=sources or None,
            provider=completion.provider,
            model=completion.model,
            tokens_prompt=completion.prompt_tokens,
            tokens_completion=completion.completion_tokens,
            latency_ms=completion.latency_ms,
        )
        conversation.provider = completion.provider
        conversation.model = completion.model

        if conversation.title.startswith("Nueva conversación"):
            conversation.title = await self._title(provider, payload.message)

        self.db.commit()
        self.db.refresh(message)

        return ChatResponse(
            conversation_id=conversation.id,
            title=conversation.title,
            message=answer,
            sources=[SourceCitation.model_validate(source) for source in sources],
            used_rag=used_rag,
            provider=completion.provider,
            model=completion.model,
            latency_ms=completion.latency_ms,
            created_at=message.created_at,
        )

    # -------------------------------------------------------- conversations
    def list_conversations(self) -> list[ConversationRead]:
        return [
            self._to_read(conversation)
            for conversation in self.conversations.list_for_user(self.user.id)
        ]

    def get_conversation(self, conversation_id: uuid.UUID) -> ConversationDetail:
        conversation = self._require(conversation_id)
        detail = self._to_read(conversation)
        return ConversationDetail(
            **detail.model_dump(),
            messages=[
                {
                    "id": message.id,
                    "conversation_id": message.conversation_id,
                    "role": message.role,
                    "content": message.content,
                    "sources": message.sources,
                    "provider": message.provider,
                    "model": message.model,
                    "latency_ms": message.latency_ms,
                    "created_at": message.created_at,
                }
                for message in conversation.messages
            ],
        )

    def rename_conversation(self, conversation_id: uuid.UUID, title: str) -> ConversationRead:
        conversation = self._require(conversation_id)
        conversation.title = title.strip()[:160]
        self.db.commit()
        self.db.refresh(conversation)
        return self._to_read(conversation)

    def delete_conversation(self, conversation_id: uuid.UUID) -> None:
        self.db.delete(self._require(conversation_id))
        self.db.commit()

    # ------------------------------------------------------------- helpers
    def _conversation(self, payload: ChatRequest) -> Conversation:
        if payload.conversation_id is not None:
            conversation = self.conversations.get_owned(self.user.id, payload.conversation_id)
            if conversation is None:
                raise NotFoundError("That conversation does not exist.", code="conversation_not_found")
            if payload.course_id is not None:
                conversation.course_id = payload.course_id
            return conversation

        conversation = Conversation(
            user_id=self.user.id,
            course_id=payload.course_id,
            title="Nueva conversación",
        )
        self.db.add(conversation)
        self.db.flush()
        return conversation

    def _require(self, conversation_id: uuid.UUID) -> Conversation:
        conversation = self.conversations.get_owned(self.user.id, conversation_id)
        if conversation is None:
            raise NotFoundError("That conversation does not exist.", code="conversation_not_found")
        return conversation

    def _student_context(self) -> str:
        courses = CourseService(self.db, self.user)
        study = StudyService(self.db, self.user)
        grades = GradeService(self.db, self.user)
        overview = grades.overview()
        upcoming = [
            f"{exam.title} ({exam.course.code if exam.course else 'sin curso'})"
            for exam in courses.exams.upcoming(self.user.id, limit=3)
        ]
        weak = [summary.course_code for summary in overview.courses[-2:]]
        return build_student_context(
            courses=[course.split(" — ")[1] for course in courses.course_names()][:6],
            upcoming=upcoming,
            average_grade=overview.overall_average,
            pending_tasks=_pending_tasks(self.db, self.user),
            study_minutes_week=study.minutes_in_range(*_week_bounds()),
            weak_topics=weak,
        )

    async def _title(self, provider, first_message: str) -> str:
        try:
            completion = await provider.complete_text(
                conversation_title_prompt(first_message),
                system="Eres un asistente que genera títulos de conversación muy cortos.",
                temperature=0.2,
                max_tokens=24,
            )
            title = " ".join(completion.content.strip().split()).strip("\"'#")
            if 3 <= len(title) <= _TITLE_MAX:
                return title
        except Exception:  # noqa: BLE001 - titles are cosmetic
            logger.debug("Title generation failed, using fallback", exc_info=True)
        return excerpt(first_message, 48) or "Nueva conversación"

    @staticmethod
    def _decorate(answer: str, *, used_rag: bool, fallback: bool) -> str:
        banner = ""
        if fallback:
            banner = (
                "> ⚠️ **Sin modelo de lenguaje conectado.** Esta respuesta se extrajo de tu "
                "material con el motor offline de STUDIA AI.\n\n"
            )
        elif not used_rag:
            banner = (
                "> ℹ️ Respondí con conocimiento general: no encontré material tuyo que cubra "
                "esta pregunta. Sube documentos para respuestas fundamentadas.\n\n"
            )
        return f"{banner}{answer.strip()}"

    def _to_read(self, conversation: Conversation) -> ConversationRead:
        return ConversationRead(
            **{
                "id": conversation.id,
                "title": conversation.title,
                "course_id": conversation.course_id,
                "course_name": conversation.course.name if conversation.course else None,
                "provider": conversation.provider,
                "model": conversation.model,
                "message_count": conversation.message_count,
                "used_rag": conversation.used_rag,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
                "last_message_at": conversation.last_message_at,
            }
        )


def _pending_tasks(db: Session, user: User) -> int:
    from sqlalchemy import func, select

    from app.models.academic import Task
    from app.models.enums import TaskStatus

    return int(
        db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user.id, Task.status != TaskStatus.COMPLETED
            )
        )
        or 0
    )


def _week_bounds() -> tuple[datetime, datetime]:
    from datetime import timedelta

    now = datetime.now(UTC)
    start = now - timedelta(days=now.weekday())
    return start, start + timedelta(days=7)