"""Flashcards (with SM-2 scheduling) and study sessions."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.course import Course
from app.models.enums import (
    FlashcardDifficulty,
    FlashcardStatus,
    StudyPlanStatus,
)
from app.models.study import Flashcard, StudyPlan, StudySession
from app.models.user import User
from app.repositories.courses import CourseRepository
from app.repositories.study import (
    FlashcardRepository,
    StudyPlanRepository,
    StudySessionRepository,
)
from app.schemas.study import (
    FlashcardCreate,
    FlashcardDeckSummary,
    FlashcardRead,
    FlashcardReviewResult,
    FlashcardUpdate,
    StudyPlanConvertRequest,
    StudyPlanDay,
    StudyPlanRead,
    StudySessionCreate,
    StudySessionRead,
)

_EASY_INTERVAL = 4
_HARD_INTERVAL = 1


class StudyService:
    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user
        self.flashcards = FlashcardRepository(db)
        self.plans = StudyPlanRepository(db)
        self.sessions = StudySessionRepository(db)
        self.courses = CourseRepository(db)

    # ----------------------------------------------------------- flashcards
    def list_flashcards(
        self,
        *,
        deck: str | None = None,
        course_id: uuid.UUID | None = None,
        search: str | None = None,
        due_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[FlashcardRead], int]:
        statement = self.flashcards.filtered(
            self.user.id, deck=deck, course_id=course_id, search=search
        )
        if due_only:
            now = datetime.now(UTC)
            statement = statement.where(
                Flashcard.status != FlashcardStatus.MASTERED,
                (Flashcard.next_review_at.is_(None) | (Flashcard.next_review_at <= now)),
            )
        rows, total = self.flashcards.paginate(statement, limit=limit, offset=offset)
        return [self._to_read(row) for row in rows], total

    def get_flashcard(self, card_id: uuid.UUID) -> FlashcardRead:
        return self._to_read(self._require_flashcard(card_id))

    def create_flashcard(self, payload: FlashcardCreate) -> FlashcardRead:
        self._validate_course(payload.course_id)
        card = Flashcard(
            user_id=self.user.id,
            next_review_at=datetime.now(UTC),
            **payload.model_dump(),
        )
        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)
        return self._to_read(card)

    def create_flashcards(self, cards: Sequence[FlashcardCreate]) -> list[FlashcardRead]:
        rows = [
            Flashcard(
                user_id=self.user.id,
                next_review_at=datetime.now(UTC),
                **card.model_dump(),
            )
            for card in cards
        ]
        self.flashcards.add_all(rows)
        self.db.commit()
        return [self._to_read(row) for row in rows]

    def update_flashcard(self, card_id: uuid.UUID, payload: FlashcardUpdate) -> FlashcardRead:
        card = self._require_flashcard(card_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            if field == "course_id" and value is not None:
                self._validate_course(value)
            setattr(card, field, value)
        self.db.commit()
        self.db.refresh(card)
        return self._to_read(card)

    def delete_flashcard(self, card_id: uuid.UUID) -> None:
        self.db.delete(self._require_flashcard(card_id))
        self.db.commit()

    def review_flashcard(self, card_id: uuid.UUID, quality: int) -> FlashcardReviewResult:
        """SM-2 scheduling step (quality 0-5)."""
        card = self._require_flashcard(card_id)
        now = datetime.now(UTC)

        if quality < 3:
            card.repetitions = 0
            card.lapses += 1
            card.interval_days = _HARD_INTERVAL
            card.ease_factor = max(1.3, card.ease_factor - 0.2)
            card.status = FlashcardStatus.LEARNING
            message = "Card returned to the learning queue. Review it again soon."
        else:
            card.repetitions += 1
            if card.repetitions == 1:
                card.interval_days = 1
            elif card.repetitions == 2:
                card.interval_days = _EASY_INTERVAL
            else:
                card.interval_days = max(1, round(card.interval_days * card.ease_factor))
            card.status = (
                FlashcardStatus.MASTERED if card.interval_days >= 21 else FlashcardStatus.REVIEW
            )
            message = (
                f"Next review in {card.interval_days} day(s)."
                if card.status == FlashcardStatus.REVIEW
                else "Card mastered."
            )

        card.ease_factor = min(2.8, round(card.ease_factor + (0.1 if quality >= 4 else 0.0), 2))
        card.last_reviewed_at = now
        card.next_review_at = now + timedelta(days=card.interval_days)
        self.db.commit()

        return FlashcardReviewResult(
            card_id=card.id,
            status=card.status,
            repetitions=card.repetitions,
            interval_days=card.interval_days,
            next_review_at=card.next_review_at,
            message=message,
        )

    def decks(self) -> list[FlashcardDeckSummary]:
        rows = self.db.scalars(self.flashcards.filtered(self.user.id)).all()
        courses = {
            course.id: course
            for course, _ in self.courses.list_for_user(self.user.id)
        }
        now = datetime.now(UTC)
        grouped: dict[str, list[Flashcard]] = {}
        for card in rows:
            grouped.setdefault(card.deck, []).append(card)

        summaries: list[FlashcardDeckSummary] = []
        for name, cards in grouped.items():
            course = courses.get(cards[0].course_id) if cards[0].course_id else None
            difficulty_scale = {
                FlashcardDifficulty.EASY: 1,
                FlashcardDifficulty.MEDIUM: 2,
                FlashcardDifficulty.HARD: 3,
            }
            summaries.append(
                FlashcardDeckSummary(
                    name=name,
                    course_id=cards[0].course_id,
                    course_name=course.name if course else None,
                    color=course.color if course else None,
                    total=len(cards),
                    new=sum(1 for card in cards if card.status == FlashcardStatus.NEW),
                    due_today=sum(
                        1
                        for card in cards
                        if card.next_review_at is None or card.next_review_at <= now
                    ),
                    mastered=sum(
                        1 for card in cards if card.status == FlashcardStatus.MASTERED
                    ),
                    average_difficulty=round(
                        sum(difficulty_scale.get(card.difficulty, 2) for card in cards)
                        / len(cards),
                        2,
                    ),
                )
            )
        summaries.sort(key=lambda item: (-item.total, item.name))
        return summaries

    # -------------------------------------------------------- study sessions
    def create_session(self, payload: StudySessionCreate) -> StudySessionRead:
        self._validate_course(payload.course_id)
        started = payload.started_at or datetime.now(UTC)
        session = StudySession(
            user_id=self.user.id,
            course_id=payload.course_id,
            study_plan_id=payload.study_plan_id,
            focus=payload.focus,
            started_at=started,
            ended_at=started + timedelta(minutes=payload.duration_minutes),
            duration_minutes=payload.duration_minutes,
            notes=payload.notes,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return self._to_session(session)

    def list_sessions(self, *, limit: int = 50, offset: int = 0) -> tuple[list[StudySessionRead], int]:
        statement = (
            select(StudySession)
            .where(StudySession.user_id == self.user.id)
            .order_by(StudySession.started_at.desc())
        )
        rows, total = self.sessions.paginate(statement, limit=limit, offset=offset)
        return [self._to_session(row) for row in rows], total

    def delete_session(self, session_id: uuid.UUID) -> None:
        session = self.db.scalars(
            select(StudySession).where(
                StudySession.id == session_id, StudySession.user_id == self.user.id
            )
        ).first()
        if session is None:
            raise NotFoundError("That study session does not exist.")
        self.db.delete(session)
        self.db.commit()

    def minutes_in_range(self, start: datetime, end: datetime) -> int:
        return self.sessions.minutes_between(self.user.id, start, end)

    def streak_days(self) -> int:
        days = {moment.date() for moment in self.sessions.days_active(self.user.id)}
        if not days:
            return 0
        today = datetime.now(UTC).date()
        cursor = today if today in days else today - timedelta(days=1)
        streak = 0
        while cursor in days:
            streak += 1
            cursor -= timedelta(days=1)
        return streak

    # ------------------------------------------------------------- plans
    def list_plans(self) -> list[StudyPlanRead]:
        return [self._to_plan(plan) for plan in self.plans.list_for_user(self.user.id)]

    def get_plan(self, plan_id: uuid.UUID) -> StudyPlanRead:
        return self._to_plan(self._require_plan(plan_id))

    def delete_plan(self, plan_id: uuid.UUID) -> None:
        self.db.delete(self._require_plan(plan_id))
        self.db.commit()

    def convert_plan(
        self, plan_id: uuid.UUID, payload: StudyPlanConvertRequest
    ) -> dict[str, list[dict]]:
        """Materialise a plan into real tasks and calendar study sessions."""
        from app.models.academic import Task
        from app.models.enums import Priority, TaskStatus

        plan = self._require_plan(plan_id)
        days = plan.days or []
        if not days:
            raise ValidationError("This plan has no days to convert.", code="empty_plan")

        start = payload.start_date or datetime.now(UTC)
        created_tasks: list[dict] = []
        created_sessions: list[dict] = []

        for offset, day in enumerate(plan_days(days)):
            day_date = _day_start(day, start) + timedelta(days=offset if not day.get("date") else 0)
            due_at = day_date.replace(hour=19, minute=0, second=0, microsecond=0)
            day_title = str(day.get("title") or f"Día {day.get('day') or offset + 1}")

            if payload.create_tasks:
                task = Task(
                    user_id=self.user.id,
                    course_id=plan.course_id,
                    title=f"{plan.title} · {day_title}",
                    description="\n".join(day.get("objectives") or []) or None,
                    due_at=due_at,
                    status=TaskStatus.PENDING,
                    priority=Priority.MEDIUM,
                    estimated_minutes=int(
                        (day.get("theory_minutes") or 0)
                        + (day.get("practice_minutes") or 0)
                        + (day.get("review_minutes") or 0)
                    ),
                )
                self.db.add(task)
                created_tasks.append({"id": str(task.id), "due_at": due_at.isoformat()})

            if payload.create_sessions:
                minutes = int(
                    (day.get("theory_minutes") or 0)
                    + (day.get("practice_minutes") or 0)
                    + (day.get("review_minutes") or 0)
                ) or plan.daily_minutes
                session = StudySession(
                    user_id=self.user.id,
                    course_id=plan.course_id,
                    study_plan_id=plan.id,
                    focus=f"{plan.title}: {day.get('focus') or day_title}",
                    started_at=due_at,
                    ended_at=due_at + timedelta(minutes=minutes),
                    duration_minutes=minutes,
                )
                self.db.add(session)
                created_sessions.append({"id": str(session.id), "started_at": due_at.isoformat()})

        plan.status = StudyPlanStatus.ACTIVE
        self.db.commit()
        self.db.refresh(plan)
        return {
            "plan": self._to_plan(plan).model_dump(mode="json"),
            "tasks": created_tasks,
            "sessions": created_sessions,
            "tasks_created": len(created_tasks),
            "sessions_created": len(created_sessions),
        }

    # ------------------------------------------------------------- helpers
    def _require_flashcard(self, card_id: uuid.UUID) -> Flashcard:
        card = self.db.scalars(
            select(Flashcard).where(
                Flashcard.id == card_id, Flashcard.user_id == self.user.id
            )
        ).first()
        if card is None:
            raise NotFoundError("That flashcard does not exist.", code="flashcard_not_found")
        return card

    def _require_plan(self, plan_id: uuid.UUID) -> StudyPlan:
        plan = self.plans.get_owned(self.user.id, plan_id)
        if plan is None:
            raise NotFoundError("That study plan does not exist.", code="plan_not_found")
        return plan

    def _validate_course(self, course_id: uuid.UUID | None) -> None:
        if course_id is None:
            return
        if self.courses.get_enrollment(self.user.id, course_id) is None:
            raise ValidationError("You are not enrolled in that course.", code="course_not_accessible")

    def _to_read(self, card: Flashcard) -> FlashcardRead:
        return FlashcardRead(
            **{
                "id": card.id,
                "front": card.front,
                "back": card.back,
                "explanation": card.explanation,
                "deck": card.deck,
                "course_id": card.course_id,
                "course": card.course,
                "origin": card.origin,
                "difficulty": card.difficulty,
                "status": card.status,
                "tags": card.tags or [],
                "source_document_id": card.source_document_id,
                "repetitions": card.repetitions,
                "lapses": card.lapses,
                "ease_factor": card.ease_factor,
                "interval_days": card.interval_days,
                "next_review_at": card.next_review_at,
                "last_reviewed_at": card.last_reviewed_at,
                "created_at": card.created_at,
            }
        )

    def _to_session(self, session: StudySession) -> StudySessionRead:
        return StudySessionRead(
            **{
                "id": session.id,
                "focus": session.focus,
                "course_id": session.course_id,
                "course": session.course,
                "study_plan_id": session.study_plan_id,
                "started_at": session.started_at,
                "ended_at": session.ended_at,
                "duration_minutes": session.duration_minutes,
                "notes": session.notes,
            }
        )

    def _to_plan(self, plan: StudyPlan) -> StudyPlanRead:
        return plan_to_read(plan)


def plan_to_read(plan: StudyPlan) -> StudyPlanRead:
    """Shared mapper so every code path returns the same shape."""
    return StudyPlanRead(
        **{
            "id": plan.id,
            "title": plan.title,
            "course_id": plan.course_id,
            "course": plan.course,
            "exam_id": plan.exam_id,
            "exam_date": plan.exam_date,
            "level": plan.level,
            "daily_minutes": plan.daily_minutes,
            "total_days": plan.total_days,
            "total_minutes": plan.total_minutes,
            "status": plan.status,
            "days": [StudyPlanDay.model_validate(day) for day in (plan.days or [])],
            "weak_topics": plan.weak_topics or [],
            "rationale": plan.rationale,
            "provider": plan.provider,
            "model": plan.model,
            "created_at": plan.created_at,
        }
    )


def plan_days(days: list[dict]) -> list[dict]:
    return sorted(days, key=lambda day: int(day.get("day") or 0))


def _day_start(day: dict, fallback: datetime) -> datetime:
    """Anchor a converted plan day on its own calendar date when available."""
    raw = day.get("date")
    if not raw:
        return fallback
    try:
        parsed = datetime.fromisoformat(str(raw))
    except ValueError:
        return fallback
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def course_lookup(db: Session, course_id: uuid.UUID) -> Course | None:
    return db.scalars(select(Course).where(Course.id == course_id)).first()


def count_cards(db: Session, user_id: uuid.UUID) -> int:
    return int(
        db.scalar(select(func.count(Flashcard.id)).where(Flashcard.user_id == user_id)) or 0
    )