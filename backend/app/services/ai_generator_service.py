"""AI generation features: summaries, questions, flashcards and explanations."""

from __future__ import annotations

import uuid
from dataclasses import replace
from typing import Any

from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.prompts import (
    STRICT_JSON_RULE,
    academic_system_prompt,
    build_student_context,
    explain_topic_prompt,
    flashcards_prompt,
    questions_prompt,
    summarize_prompt,
)
from app.ai.rag.parsing import ensure_list, extract_json
from app.ai.rag.retriever import Retriever
from app.ai.registry import resolve_provider
from app.core.errors import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models.document import Document
from app.models.enums import (
    Difficulty,
    FlashcardDifficulty,
    FlashcardOrigin,
    FlashcardStatus,
    QuestionType,
    StudyLevel,
    SummaryStyle,
)
from app.models.user import User
from app.repositories.courses import CourseRepository
from app.repositories.documents import DocumentRepository
from app.schemas.ai import (
    ExplainResult,
    GeneratedQuestion,
    GenerateQuestionsRequest,
    GenerateQuestionsResult,
    GradeAnswersRequest,
    GradeAnswersResult,
    GradedAnswer,
)
from app.schemas.document import SourceCitation, SummaryRequest, SummaryResult
from app.schemas.study import (
    FlashcardCreate,
    FlashcardRead,
    GenerateFlashcardsRequest,
    GenerateFlashcardsResult,
)
from app.services.academic_service import GradeService
from app.services.course_service import CourseService
from app.services.study_service import StudyService
from app.utils.text import excerpt

logger = get_logger("app.ai.generators")


class GeneratorService:
    """Everything that turns documents into study material."""

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user
        self.documents = DocumentRepository(db)
        self.courses = CourseRepository(db)

    # ------------------------------------------------------------ summarize
    async def summarize(self, payload: SummaryRequest) -> SummaryResult:
        resolved = await resolve_provider()
        provider = resolved.provider
        documents = self._require_documents(payload.document_ids)
        context = await self._context_for(
            provider,
            documents,
            focus=payload.focus or "conceptos principales",
            limit=10,
        )
        prompt = summarize_prompt(
            context=context.context_text,
            style=payload.style,
            student_data=self._student_data(),
            focus=payload.focus,
        )
        completion = await provider.complete_text(
            prompt,
            system=academic_system_prompt(),
            temperature=0.2,
            max_tokens=900 if payload.style != SummaryStyle.SHORT else 450,
        )
        return SummaryResult(
            summary=self._with_disclosure(completion.content, resolved.used_fallback),
            style=payload.style,
            sources=[source.model_dump() for source in context.sources],
            provider=completion.provider,
            model=completion.model,
            tokens=completion.completion_tokens,
        )

    # ------------------------------------------------------------ questions
    async def questions(self, payload: GenerateQuestionsRequest) -> GenerateQuestionsResult:
        resolved = await resolve_provider()
        provider = resolved.provider
        documents = self._require_documents(payload.document_ids) if payload.document_ids else []
        context = await self._context_for(
            provider, documents, focus="evaluación", limit=max(payload.count * 2, 8)
        )
        prompt = questions_prompt(
            context=context.context_text,
            count=payload.count,
            types=payload.question_types,
            difficulty=payload.difficulty,
            topics=payload.topics,
            student_data=self._student_data(),
        )
        completion = await provider.complete_text(
            prompt,
            system=f"{academic_system_prompt()}\n{STRICT_JSON_RULE}",
            temperature=0.4,
            json_mode=True,
            max_tokens=2400,
        )
        parsed = _safe_json(completion.content)
        questions = self._normalize_questions(parsed, payload)
        if not questions:
            # The offline engine must never leave the student without questions
            # when there is material to mine.
            questions = _mined_questions(context.context_text, payload)
        if not questions:
            raise ValidationError(
                "The AI did not return usable questions. Try again with a different document.",
                code="empty_questions",
            )
        return GenerateQuestionsResult(
            questions=questions[: payload.count],
            provider=completion.provider,
            model=completion.model,
            sources=[source.model_dump() for source in context.sources],
            count=min(len(questions), payload.count),
        )

    def grade_answers(
        self, questions: list[GeneratedQuestion], payload: GradeAnswersRequest
    ) -> GradeAnswersResult:
        index = {question.id: question for question in questions}
        graded: list[GradedAnswer] = []
        correct = 0
        for answer in payload.questions:
            question = index.get(answer.question_id)
            if question is None:
                continue
            is_correct = _matches(question, answer.answer)
            correct += int(is_correct)
            graded.append(
                GradedAnswer(
                    question_id=question.id,
                    is_correct=is_correct,
                    expected_answer=question.correct_answer,
                    explanation=question.explanation,
                    awarded_points=1.0 if is_correct else 0.0,
                    max_points=1.0,
                )
            )
        total = len(graded)
        score = round((correct / total) * 100, 2) if total else 0.0
        return GradeAnswersResult(
            score=score,
            correct_count=correct,
            total=total,
            answers=graded,
            feedback=_feedback(score, graded),
        )

    # ----------------------------------------------------------- flashcards
    async def flashcards(self, payload: GenerateFlashcardsRequest) -> GenerateFlashcardsResult:
        resolved = await resolve_provider()
        provider = resolved.provider
        documents = self._require_documents(payload.document_ids)
        context = await self._context_for(
            provider, documents, focus=payload.focus or "conceptos clave", limit=12
        )
        prompt = flashcards_prompt(
            context=context.context_text,
            count=payload.count,
            difficulty=Difficulty(payload.difficulty.value),
            focus=payload.focus,
            student_data=self._student_data(),
        )
        completion = await provider.complete_text(
            prompt,
            system=f"{academic_system_prompt()}\n{STRICT_JSON_RULE}",
            temperature=0.5,
            json_mode=True,
            max_tokens=2400,
        )
        parsed = _safe_json(completion.content)
        cards = self._normalize_flashcards(parsed, payload, documents)
        created: list[FlashcardRead] = []
        if payload.save and cards:
            created = StudyService(self.db, self.user).create_flashcards(cards)
        preview = created or [
            FlashcardRead(
                id=uuid.uuid4(),
                front=card.front,
                back=card.back,
                explanation=card.explanation,
                deck=card.deck,
                course_id=card.course_id,
                origin=card.origin,
                difficulty=card.difficulty,
                status=FlashcardStatus.NEW,
                repetitions=0,
                lapses=0,
                ease_factor=2.5,
                interval_days=0,
                next_review_at=_now(),
                created_at=_now(),
            )
            for card in cards
        ]
        return GenerateFlashcardsResult(
            flashcards=preview,
            created=len(created),
            sources=[source.model_dump() for source in context.sources],
            provider=completion.provider,
            model=completion.model,
        )

    # ------------------------------------------------------------- explain
    async def explain(
        self, *, topic: str, course_id: uuid.UUID | None, level: StudyLevel, document_ids: list[uuid.UUID], use_rag: bool
    ) -> ExplainResult:
        resolved = await resolve_provider()
        provider = resolved.provider
        documents = self._require_documents(document_ids) if document_ids else []
        context = await self._context_for(provider, documents, focus=topic, limit=8) if use_rag else None
        prompt = explain_topic_prompt(
            topic=topic,
            level=level,
            context=context.context_text if context else "",
            student_data=self._student_data(),
        )
        completion = await provider.complete_text(
            prompt,
            system=academic_system_prompt(),
            temperature=0.35,
            max_tokens=1200,
        )
        return ExplainResult(
            topic=topic,
            level=level,
            answer=self._with_disclosure(completion.content, resolved.used_fallback),
            sources=[
                source.model_dump(mode="json")
                for source in (context.sources if context else [])
            ],
            used_rag=bool(context and context.used_rag),
            provider=completion.provider,
            model=completion.model,
        )

    # ------------------------------------------------------------- helpers
    async def _context_for(
        self,
        provider: AIProvider,
        documents: list[Document],
        *,
        focus: str,
        limit: int,
    ):
        retriever = Retriever(self.db, provider, self.user.id)
        ids = [document.id for document in documents] or None
        context = await retriever.retrieve(focus, document_ids=ids, top_k=limit, min_score=0.0)
        if documents and not context.sources:
            # The focus phrase may match nothing (for example "conceptos
            # principales"), but a summary of an explicitly chosen document
            # must still cite it.
            context = self._context_from_leading_chunks(context, documents)
        return context

    def _context_from_leading_chunks(self, context, documents: list[Document]):
        from app.ai.rag.retriever import RetrievedChunk

        chunks: list[RetrievedChunk] = []
        sources: list[SourceCitation] = []
        for document in documents:
            stored = self.documents.chunks(document.id, limit=1)
            if not stored:
                continue
            chunk = stored[0]
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    heading=chunk.heading,
                    page_number=chunk.page_number,
                    score=0.0,
                )
            )
            sources.append(
                SourceCitation(
                    document_id=document.id,
                    title=document.title,
                    filename=document.filename,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    excerpt=excerpt(chunk.content, 320),
                )
            )
        return replace(context, chunks=chunks, sources=sources, used_rag=bool(chunks))

    def _require_documents(self, document_ids: list[uuid.UUID]) -> list[Document]:
        documents = self.documents.get_many_owned(self.user.id, document_ids)
        if not documents:
            if not document_ids:
                raise ValidationError(
                    "Select at least one document you own.", code="no_documents"
                )
            raise NotFoundError(
                "None of those documents are available.", code="document_not_found"
            )
        return documents

    def _student_data(self) -> str:
        courses = CourseService(self.db, self.user)
        study = StudyService(self.db, self.user)
        overview = GradeService(self.db, self.user).overview()
        from datetime import UTC, datetime, timedelta

        now = datetime.now(UTC)
        upcoming = [
            f"{exam.title} ({exam.course.code if exam.course else 'sin curso'}) en {max(0, (exam.scheduled_at - now).days)} días"
            for exam in courses.exams.upcoming(self.user.id, limit=3)
        ]
        return build_student_context(
            courses=[name.split(" — ")[1] for name in courses.course_names()][:6],
            upcoming=upcoming,
            average_grade=overview.overall_average,
            pending_tasks=_pending(self.db, self.user),
            study_minutes_week=study.minutes_in_range(now - timedelta(days=now.weekday()), now),
            weak_topics=[item.course_code for item in overview.courses[-2:]],
        )

    def _normalize_questions(
        self, parsed: Any, payload: GenerateQuestionsRequest
    ) -> list[GeneratedQuestion]:
        questions: list[GeneratedQuestion] = []
        for index, item in enumerate(ensure_list(parsed, "questions"), start=1):
            prompt_text = str(item.get("prompt") or item.get("question") or "").strip()
            if not prompt_text:
                continue
            try:
                question_type = QuestionType(str(item.get("type") or payload.question_types[0].value))
            except ValueError:
                question_type = payload.question_types[0]
            options = [
                {"id": str(option.get("id") or chr(65 + position)), "text": str(option.get("text", ""))}
                for position, option in enumerate(item.get("options") or [])
                if isinstance(option, dict) and option.get("text")
            ]
            correct = str(item.get("correct_answer") or item.get("answer") or "")
            correct_id = item.get("correct_option_id")
            if correct_id is None and options and correct in {option["id"] for option in options}:
                correct_id = correct
            if question_type in {QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE}:
                if not options:
                    continue
                if correct_id not in {option["id"] for option in options}:
                    correct_id = options[0]["id"]
                correct = str(correct_id)
            questions.append(
                GeneratedQuestion(
                    id=str(item.get("id") or f"q{index}"),
                    type=question_type,
                    prompt=prompt_text,
                    options=options,
                    correct_answer=correct,
                    correct_option_id=str(correct_id) if correct_id else None,
                    explanation=str(item.get("explanation") or "").strip(),
                    difficulty=_difficulty(item.get("difficulty"), payload.difficulty),
                    topic=str(item.get("topic")) if item.get("topic") else None,
                )
            )
        return questions

    def _normalize_flashcards(
        self,
        parsed: Any,
        payload: GenerateFlashcardsRequest,
        documents: list[Document],
    ) -> list[FlashcardCreate]:
        cards: list[FlashcardCreate] = []
        for item in ensure_list(parsed, "flashcards"):
            front = str(item.get("front") or item.get("question") or "").strip()
            back = str(item.get("back") or item.get("answer") or "").strip()
            if not front or not back:
                continue
            cards.append(
                FlashcardCreate(
                    front=front[:1000],
                    back=back[:2000],
                    explanation=str(item.get("explanation") or "")[:2000] or None,
                    deck=payload.deck,
                    course_id=payload.course_id,
                    difficulty=FlashcardDifficulty(
                        str(item.get("difficulty") or payload.difficulty.value)
                        if str(item.get("difficulty") or payload.difficulty.value)
                        in {item.value for item in FlashcardDifficulty}
                        else payload.difficulty.value
                    ),
                    origin=FlashcardOrigin.AI,
                    source_document_id=documents[0].id if documents else None,
                )
            )
        return cards

    @staticmethod
    def _with_disclosure(content: str, fallback: bool) -> str:
        if not fallback:
            return content.strip()
        return (
            "> ⚠️ **Sin modelo de lenguaje conectado:** contenido extraído de tu material "
            "con el motor offline de STUDIA AI.\n\n"
            f"{content.strip()}"
        )


# ---------------------------------------------------------------- helpers
def _safe_json(text: str) -> Any:
    try:
        return extract_json(text)
    except ValueError:
        logger.warning("Model returned non-JSON content: %s", excerpt(text, 200))
        return {}


def _mined_questions(
    context_text: str, payload: GenerateQuestionsRequest
) -> list[GeneratedQuestion]:
    """Deterministic cloze questions mined from the retrieved context."""
    from app.ai.providers.local import LocalProvider
    from app.utils.text import split_sentences

    provider = LocalProvider()
    sentences = [
        sentence
        for block in context_text.splitlines()
        for sentence in split_sentences(block)
        if len(sentence.split()) >= 6
    ][: payload.count * 3]

    questions: list[GeneratedQuestion] = []
    for index, sentence in enumerate(sentences, start=1):
        key_term = provider._pick_key_term(sentence)
        if not key_term:
            continue
        if index % 3 == 0:
            questions.append(
                GeneratedQuestion(
                    id=f"q{len(questions) + 1}",
                    type=QuestionType.TRUE_FALSE,
                    prompt=f"Verdadero o falso: {sentence}",
                    options=[
                        {"id": "A", "text": "Verdadero"},
                        {"id": "B", "text": "Falso"},
                    ],
                    correct_answer="A",
                    correct_option_id="A",
                    explanation=f"Extraído literalmente del material: «{excerpt(sentence, 240)}».",
                    difficulty=payload.difficulty,
                    topic=key_term,
                )
            )
        else:
            distractors = provider._distractors(key_term, " ".join(sentences))
            options = [{"id": "A", "text": key_term}]
            options.extend(
                {"id": chr(66 + position), "text": term}
                for position, term in enumerate(distractors)
            )
            questions.append(
                GeneratedQuestion(
                    id=f"q{len(questions) + 1}",
                    type=QuestionType.MULTIPLE_CHOICE,
                    prompt=sentence.replace(key_term, "____", 1),
                    options=options,
                    correct_answer="A",
                    correct_option_id="A",
                    explanation=f"La respuesta correcta es «{key_term}».",
                    difficulty=payload.difficulty,
                    topic=key_term,
                )
            )
        if len(questions) >= payload.count:
            break
    return questions


def _difficulty(value: Any, default: Difficulty) -> Difficulty:
    try:
        return Difficulty(str(value))
    except ValueError:
        return default


def _matches(question: GeneratedQuestion, answer: str) -> bool:
    normalized = answer.strip().lower()
    if not normalized:
        return False
    expected = question.correct_answer.strip().lower()
    if question.correct_option_id:
        target = question.correct_option_id.strip().lower()
        if normalized == target:
            return True
        if normalized and normalized[0] == target[0] and len(normalized) <= 3:
            return True
    if expected and normalized == expected:
        return True
    if question.type == QuestionType.SHORT_ANSWER:
        return expected and (expected in normalized or normalized in expected)
    if question.type == QuestionType.TRUE_FALSE:
        truthy = {"verdadero", "true", "v", "t", "1", "si", "sí"}
        falsy = {"falso", "false", "f", "0", "no"}
        return normalized in (truthy if expected in truthy else falsy)
    return False


def _feedback(score: float, graded: list[GradedAnswer]) -> str:
    wrong = [item for item in graded if not item.is_correct]
    if not wrong:
        return "Perfect score. Try a harder difficulty next round."
    topics = ", ".join(
        item.explanation.split(".")[0][:60] for item in wrong[:2] if item.explanation
    )
    tail = f" Revisa: {topics}." if topics else ""
    if score >= 70:
        return f"Solid result ({score}%).{tail}"
    if score >= 40:
        return f"You're halfway there ({score}%).{tail}"
    return f"This topic needs another pass ({score}%).{tail}"


def _pending(db: Session, user: User) -> int:
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


def _now():
    from datetime import UTC, datetime

    return datetime.now(UTC)