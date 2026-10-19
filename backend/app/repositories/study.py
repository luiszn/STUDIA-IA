"""Study repository: flashcards, conversations, plans, sessions, recommendations."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, func, select

from app.models.study import (
    Conversation,
    Flashcard,
    Message,
    Recommendation,
    StudyPlan,
    StudySession,
)
from app.repositories.base import BaseRepository


class FlashcardRepository(BaseRepository[Flashcard]):
    model = Flashcard

    def query_for_user(self, user_id: uuid.UUID) -> Select:
        return select(Flashcard).where(Flashcard.user_id == user_id)

    def filtered(
        self,
        user_id: uuid.UUID,
        *,
        deck: str | None = None,
        course_id: uuid.UUID | None = None,
        search: str | None = None,
    ) -> Select:
        statement = self.query_for_user(user_id)
        if deck:
            statement = statement.where(Flashcard.deck == deck)
        if course_id is not None:
            statement = statement.where(Flashcard.course_id == course_id)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                Flashcard.front.ilike(pattern) | Flashcard.back.ilike(pattern)
            )
        return statement.order_by(Flashcard.created_at.desc())

    def decks(self, user_id: uuid.UUID) -> Sequence[str]:
        return list(
            self.db.scalars(
                select(Flashcard.deck)
                .where(Flashcard.user_id == user_id)
                .group_by(Flashcard.deck)
                .order_by(func.count(Flashcard.id).desc())
            ).all()
        )

    def due(self, user_id: uuid.UUID, *, now: datetime | None = None) -> Sequence[Flashcard]:
        now = now or datetime.now(UTC)
        return self.db.scalars(
            self.query_for_user(user_id)
            .where(
                Flashcard.status != "mastered",
                (Flashcard.next_review_at.is_(None) | (Flashcard.next_review_at <= now)),
            )
            .order_by(func.coalesce(Flashcard.next_review_at, Flashcard.created_at))
        ).all()

    def total_for_user(self, user_id: uuid.UUID) -> int:
        return int(
            self.db.scalar(select(func.count(Flashcard.id)).where(Flashcard.user_id == user_id)) or 0
        )


class ConversationRepository(BaseRepository[Conversation]):
    model = Conversation

    def list_for_user(self, user_id: uuid.UUID) -> Sequence[Conversation]:
        return self.db.scalars(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(func.coalesce(Conversation.last_message_at, Conversation.created_at).desc())
        ).all()

    def get_owned(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> Conversation | None:
        return self.db.scalars(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.user_id == user_id
            )
        ).first()

    def recent_messages(self, conversation_id: uuid.UUID, limit: int = 20) -> Sequence[Message]:
        rows = self.db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        ).all()
        return list(reversed(rows))

    def add_message(self, conversation: Conversation, **values: object) -> Message:
        # `user_id` is denormalised on purpose so messages stay queryable
        # (and deletable) without joining through the conversation.
        message = Message(
            conversation_id=conversation.id,
            user_id=conversation.user_id,
            **values,  # type: ignore[arg-type]
        )
        conversation.message_count += 1
        conversation.last_message_at = datetime.now(UTC)
        self.db.add(message)
        self.db.flush()
        return message


class StudyPlanRepository(BaseRepository[StudyPlan]):
    model = StudyPlan

    def list_for_user(self, user_id: uuid.UUID) -> Sequence[StudyPlan]:
        return self.db.scalars(
            select(StudyPlan)
            .where(StudyPlan.user_id == user_id)
            .order_by(StudyPlan.created_at.desc())
        ).all()

    def get_owned(self, user_id: uuid.UUID, plan_id: uuid.UUID) -> StudyPlan | None:
        return self.db.scalars(
            select(StudyPlan).where(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
        ).first()


class StudySessionRepository(BaseRepository[StudySession]):
    model = StudySession

    def minutes_between(self, user_id: uuid.UUID, start: datetime, end: datetime) -> int:
        total = self.db.scalar(
            select(func.coalesce(func.sum(StudySession.duration_minutes), 0)).where(
                StudySession.user_id == user_id,
                StudySession.started_at >= start,
                StudySession.started_at < end,
            )
        )
        return int(total or 0)

    def days_active(self, user_id: uuid.UUID, *, since_days: int = 120) -> Sequence[datetime]:
        return list(
            self.db.scalars(
                select(StudySession.started_at).where(
                    StudySession.user_id == user_id,
                    StudySession.started_at >= datetime.now(UTC) - timedelta(days=since_days),
                )
            ).all()
        )

    def total_minutes(self, user_id: uuid.UUID) -> int:
        total = self.db.scalar(
            select(func.coalesce(func.sum(StudySession.duration_minutes), 0)).where(
                StudySession.user_id == user_id
            )
        )
        return int(total or 0)


class RecommendationRepository(BaseRepository[Recommendation]):
    model = Recommendation

    def active_for_user(self, user_id: uuid.UUID, *, limit: int = 10) -> Sequence[Recommendation]:
        now = datetime.now(UTC)
        statement = (
            select(Recommendation)
            .where(
                Recommendation.user_id == user_id,
                Recommendation.is_dismissed.is_(False),
                (Recommendation.expires_at.is_(None) | (Recommendation.expires_at >= now)),
            )
            .order_by(Recommendation.score.desc(), Recommendation.created_at.desc())
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def unread_count(self, user_id: uuid.UUID) -> int:
        return int(
            self.db.scalar(
                select(func.count(Recommendation.id)).where(
                    Recommendation.user_id == user_id,
                    Recommendation.is_dismissed.is_(False),
                    Recommendation.is_read.is_(False),
                )
            )
            or 0
        )