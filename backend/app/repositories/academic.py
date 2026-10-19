"""Academic repository: tasks, exams and grades."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import Select, func, or_, select

from app.models.academic import Exam, Grade, Task
from app.models.enums import ExamStatus, Priority, TaskStatus
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    model = Task

    def query_for_user(self, user_id: uuid.UUID) -> Select:
        return select(Task).where(Task.user_id == user_id)

    def filtered(
        self,
        user_id: uuid.UUID,
        *,
        status: TaskStatus | None = None,
        priority: Priority | None = None,
        course_id: uuid.UUID | None = None,
        due_after: datetime | None = None,
        due_before: datetime | None = None,
        search: str | None = None,
    ) -> Select:
        statement = self.query_for_user(user_id)
        if status is not None:
            statement = statement.where(Task.status == status)
        if priority is not None:
            statement = statement.where(Task.priority == priority)
        if course_id is not None:
            statement = statement.where(Task.course_id == course_id)
        if due_after is not None:
            statement = statement.where(Task.due_at >= due_after)
        if due_before is not None:
            statement = statement.where(Task.due_at <= due_before)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(Task.title.ilike(pattern), Task.description.ilike(pattern))
            )
        return statement

    def count_by_status(self, user_id: uuid.UUID, status: TaskStatus) -> int:
        return int(
            self.db.scalar(
                select(func.count(Task.id)).where(Task.user_id == user_id, Task.status == status)
            )
            or 0
        )

    def count_overdue(self, user_id: uuid.UUID, now: datetime | None = None) -> int:
        now = now or datetime.now(UTC)
        return int(
            self.db.scalar(
                select(func.count(Task.id)).where(
                    Task.user_id == user_id,
                    Task.status != TaskStatus.COMPLETED,
                    Task.due_at.is_not(None),
                    Task.due_at < now,
                )
            )
            or 0
        )

    def due_within(self, user_id: uuid.UUID, days: int) -> Sequence[Task]:
        now = datetime.now(UTC)
        return self.db.scalars(
            self.filtered(user_id, due_after=now, due_before=_add_days(now, days)).order_by(
                Task.due_at
            )
        ).all()


class ExamRepository(BaseRepository[Exam]):
    model = Exam

    def upcoming(self, user_id: uuid.UUID, *, limit: int = 10) -> Sequence[Exam]:
        return self.db.scalars(
            select(Exam)
            .where(
                Exam.user_id == user_id,
                Exam.status == ExamStatus.SCHEDULED,
                Exam.scheduled_at >= datetime.now(UTC),
            )
            .order_by(Exam.scheduled_at)
            .limit(limit)
        ).all()

    def between(self, user_id: uuid.UUID, start: datetime, end: datetime) -> Sequence[Exam]:
        return self.db.scalars(
            select(Exam)
            .where(
                Exam.user_id == user_id,
                Exam.scheduled_at >= start,
                Exam.scheduled_at <= end,
            )
            .order_by(Exam.scheduled_at)
        ).all()

    def next_exam(self, user_id: uuid.UUID) -> Exam | None:
        return self.db.scalars(
            select(Exam)
            .where(
                Exam.user_id == user_id,
                Exam.status == ExamStatus.SCHEDULED,
                Exam.scheduled_at >= datetime.now(UTC),
            )
            .order_by(Exam.scheduled_at)
            .limit(1)
        ).first()


class GradeRepository(BaseRepository[Grade]):
    model = Grade

    def for_user(self, user_id: uuid.UUID, *, course_id: uuid.UUID | None = None) -> Select:
        statement = select(Grade).where(Grade.user_id == user_id)
        if course_id is not None:
            statement = statement.where(Grade.course_id == course_id)
        return statement.order_by(Grade.graded_at.desc(), Grade.created_at.desc())

    def percentages(self, user_id: uuid.UUID) -> list[tuple[uuid.UUID, float]]:
        rows = self.db.execute(
            select(Grade.course_id, Grade.score, Grade.max_score).where(Grade.user_id == user_id)
        ).all()
        return [
            (course_id, (score / max_score) * 100)
            for course_id, score, max_score in rows
            if max_score
        ]

    def overall_average(self, user_id: uuid.UUID) -> float | None:
        values = [percentage for _, percentage in self.percentages(user_id)]
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    def trend(self, user_id: uuid.UUID, limit: int = 12) -> list[float]:
        rows = self.db.scalars(self.for_user(user_id).limit(limit)).all()
        return [round((grade.score / grade.max_score) * 100, 2) for grade in rows if grade.max_score]


def _add_days(moment: datetime, days: int) -> datetime:
    from datetime import timedelta

    return moment + timedelta(days=days)