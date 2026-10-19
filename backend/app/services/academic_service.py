"""Task, exam and grade services plus academic analytics."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.academic import Exam, Grade, Task
from app.models.enums import (
    ExamStatus,
    Priority,
    TaskStatus,
)
from app.models.user import User
from app.repositories.academic import ExamRepository, GradeRepository, TaskRepository
from app.repositories.courses import CourseRepository
from app.schemas.academic import (
    CourseGradeSummary,
    ExamCreate,
    ExamRead,
    ExamUpdate,
    GradeCreate,
    GradeOverview,
    GradeRead,
    GradeUpdate,
    TaskCreate,
    TaskRead,
    TaskUpdate,
)

PASSING_SCORE = 60.0


class TaskService:
    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user
        self.repo = TaskRepository(db)
        self.courses = CourseRepository(db)

    def list(
        self,
        *,
        status: TaskStatus | None = None,
        priority: Priority | None = None,
        course_id: uuid.UUID | None = None,
        due_before: datetime | None = None,
        due_after: datetime | None = None,
        search: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[TaskRead], int]:
        statement = self.repo.filtered(
            self.user.id,
            status=status,
            priority=priority,
            course_id=course_id,
            due_before=due_before,
            due_after=due_after,
            search=search,
        ).order_by(Task.due_at.is_(None), Task.due_at, Task.priority.desc(), Task.position)
        rows, total = self.repo.paginate(statement, limit=limit, offset=offset)
        return [self._to_read(row) for row in rows], total

    def get(self, task_id: uuid.UUID) -> TaskRead:
        return self._to_read(self._require(task_id))

    def create(self, payload: TaskCreate) -> TaskRead:
        self._validate_course(payload.course_id)
        task = Task(
            user_id=self.user.id,
            **{**payload.model_dump(exclude={"course_id"}), "course_id": payload.course_id},
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return self._to_read(task)

    def update(self, task_id: uuid.UUID, payload: TaskUpdate) -> TaskRead:
        task = self._require(task_id)
        values = payload.model_dump(exclude_unset=True)
        self._validate_course(values.get("course_id"))
        for field, value in values.items():
            setattr(task, field, value)
        if values.get("status") == TaskStatus.COMPLETED and task.completed_at is None:
            task.completed_at = datetime.now(UTC)
        elif values.get("status") and values["status"] != TaskStatus.COMPLETED:
            task.completed_at = None
        self.db.commit()
        self.db.refresh(task)
        return self._to_read(task)

    def toggle(self, task_id: uuid.UUID) -> TaskRead:
        task = self._require(task_id)
        if task.status == TaskStatus.COMPLETED:
            task.status = TaskStatus.PENDING
            task.completed_at = None
        else:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(task)
        return self._to_read(task)

    def delete(self, task_id: uuid.UUID) -> None:
        self.db.delete(self._require(task_id))
        self.db.commit()

    # ------------------------------------------------------------- helpers
    def _require(self, task_id: uuid.UUID) -> Task:
        from sqlalchemy import select

        task = self.db.scalars(
            select(Task).where(Task.id == task_id, Task.user_id == self.user.id)
        ).first()
        if task is None:
            raise NotFoundError("That task does not exist.", code="task_not_found")
        return task

    def _validate_course(self, course_id: uuid.UUID | None) -> None:
        if course_id is None:
            return
        if self.courses.get_enrollment(self.user.id, course_id) is None:
            raise ValidationError("You are not enrolled in that course.", code="course_not_accessible")

    def _to_read(self, task: Task) -> TaskRead:
        return TaskRead(
            **{
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "course_id": task.course_id,
                "course": task.course,
                "status": task.status,
                "priority": task.priority,
                "due_at": task.due_at,
                "completed_at": task.completed_at,
                "estimated_minutes": task.estimated_minutes,
                "is_overdue": task.is_overdue(),
                "created_at": task.created_at,
                "updated_at": task.updated_at,
            }
        )


class ExamService:
    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user
        self.repo = ExamRepository(db)
        self.courses = CourseRepository(db)

    def list(
        self,
        *,
        course_id: uuid.UUID | None = None,
        status: ExamStatus | None = None,
        upcoming_only: bool = False,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ExamRead], int]:
        from sqlalchemy import select

        statement = select(Exam).where(Exam.user_id == self.user.id)
        if course_id is not None:
            statement = statement.where(Exam.course_id == course_id)
        if status is not None:
            statement = statement.where(Exam.status == status)
        if upcoming_only:
            statement = statement.where(Exam.scheduled_at >= datetime.now(UTC))
        if from_date is not None:
            statement = statement.where(Exam.scheduled_at >= from_date)
        if to_date is not None:
            statement = statement.where(Exam.scheduled_at <= to_date)
        statement = statement.order_by(Exam.scheduled_at)

        rows, total = self.repo.paginate(statement, limit=limit, offset=offset)
        return [self._to_read(row) for row in rows], total

    def get(self, exam_id: uuid.UUID) -> ExamRead:
        return self._to_read(self._require(exam_id))

    def create(self, payload: ExamCreate) -> ExamRead:
        if self.courses.get_enrollment(self.user.id, payload.course_id) is None:
            raise ValidationError("You are not enrolled in that course.", code="course_not_accessible")
        exam = Exam(user_id=self.user.id, **payload.model_dump())
        self.db.add(exam)
        self.db.commit()
        self.db.refresh(exam)
        return self._to_read(exam)

    def update(self, exam_id: uuid.UUID, payload: ExamUpdate) -> ExamRead:
        exam = self._require(exam_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(exam, field, value)
        self.db.commit()
        self.db.refresh(exam)
        return self._to_read(exam)

    def delete(self, exam_id: uuid.UUID) -> None:
        self.db.delete(self._require(exam_id))
        self.db.commit()

    def _require(self, exam_id: uuid.UUID) -> Exam:
        from sqlalchemy import select

        exam = self.db.scalars(
            select(Exam).where(Exam.id == exam_id, Exam.user_id == self.user.id)
        ).first()
        if exam is None:
            raise NotFoundError("That exam does not exist.", code="exam_not_found")
        return exam

    def _to_read(self, exam: Exam) -> ExamRead:
        days_until = None
        delta = exam.scheduled_at - datetime.now(UTC)
        if delta.total_seconds() >= 0:
            days_until = delta.days
        grade = next(
            (grade for grade in (exam.grades or []) if not grade.is_projection), None
        )
        return ExamRead(
            **{
                "id": exam.id,
                "title": exam.title,
                "course_id": exam.course_id,
                "course": exam.course,
                "exam_type": exam.exam_type,
                "status": exam.status,
                "scheduled_at": exam.scheduled_at,
                "duration_minutes": exam.duration_minutes,
                "location": exam.location,
                "notes": exam.notes,
                "weight": exam.weight,
                "topics": exam.topics,
                "days_until": days_until,
                "grade_id": grade.id if grade else None,
                "created_at": exam.created_at,
            }
        )


class GradeService:
    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user
        self.repo = GradeRepository(db)
        self.courses = CourseRepository(db)

    def list(
        self, *, course_id: uuid.UUID | None = None, limit: int = 100, offset: int = 0
    ) -> tuple[list[GradeRead], int]:
        statement = self.repo.for_user(self.user.id, course_id=course_id)
        rows, total = self.repo.paginate(statement, limit=limit, offset=offset)
        return [self._to_read(row) for row in rows], total

    def get(self, grade_id: uuid.UUID) -> GradeRead:
        from sqlalchemy import select

        grade = self.db.scalars(
            select(Grade).where(Grade.id == grade_id, Grade.user_id == self.user.id)
        ).first()
        if grade is None:
            raise NotFoundError("That grade does not exist.", code="grade_not_found")
        return self._to_read(grade)

    def create(self, payload: GradeCreate) -> GradeRead:
        if self.courses.get_enrollment(self.user.id, payload.course_id) is None:
            raise ValidationError("You are not enrolled in that course.", code="course_not_accessible")
        if payload.score > payload.max_score:
            raise ValidationError("The score cannot be higher than the maximum score.")
        values = payload.model_dump()
        if values.get("graded_on_date") is None:
            values["graded_on_date"] = datetime.now(UTC).date()
        grade = Grade(user_id=self.user.id, **values)
        self.db.add(grade)
        self._sync_exam_status(grade)
        self.db.commit()
        self.db.refresh(grade)
        return self._to_read(grade)

    def update(self, grade_id: uuid.UUID, payload: GradeUpdate) -> GradeRead:
        from sqlalchemy import select

        grade = self.db.scalars(
            select(Grade).where(Grade.id == grade_id, Grade.user_id == self.user.id)
        ).first()
        if grade is None:
            raise NotFoundError("That grade does not exist.", code="grade_not_found")
        values = payload.model_dump(exclude_unset=True)
        max_score = values.get("max_score", grade.max_score)
        score = values.get("score", grade.score)
        if score > max_score:
            raise ValidationError("The score cannot be higher than the maximum score.")
        for field, value in values.items():
            setattr(grade, field, value)
        self.db.commit()
        self.db.refresh(grade)
        return self._to_read(grade)

    def delete(self, grade_id: uuid.UUID) -> None:
        from sqlalchemy import select

        grade = self.db.scalars(
            select(Grade).where(Grade.id == grade_id, Grade.user_id == self.user.id)
        ).first()
        if grade is None:
            raise NotFoundError("That grade does not exist.", code="grade_not_found")
        self.db.delete(grade)
        self.db.commit()

    # ------------------------------------------------------------ overview
    def overview(self) -> GradeOverview:
        courses = {
            course.id: course
            for course, _ in self.courses.list_for_user(self.user.id)
        }
        rows = self.db.scalars(self.repo.for_user(self.user.id)).all()

        buckets: dict[uuid.UUID, list[float]] = {}
        categories: dict[str, list[float]] = {}
        recent: list[GradeRead] = []
        for grade in rows:
            percentage = grade.percentage
            buckets.setdefault(grade.course_id, []).append(percentage)
            categories.setdefault(grade.category, []).append(percentage)
            recent.append(self._to_read(grade))

        summaries: list[CourseGradeSummary] = []
        for course_id, values in buckets.items():
            course = courses.get(course_id)
            if course is None:
                continue
            average = round(sum(values) / len(values), 2)
            summaries.append(
                CourseGradeSummary(
                    course_id=course_id,
                    course_name=course.name,
                    course_code=course.code,
                    color=course.color,
                    average=average,
                    highest=round(max(values), 2),
                    lowest=round(min(values), 2),
                    count=len(values),
                    projected=self._projection(values),
                    required_to_pass=self._needed_for_pass(values),
                    trend=list(reversed(values[-8:])),
                )
            )
        summaries.sort(key=lambda item: item.average)

        overall = self.repo.overall_average(self.user.id)
        return GradeOverview(
            overall_average=overall,
            courses=summaries,
            distribution=self._distribution(rows),
            category_breakdown=[
                {"category": key, "average": round(sum(values) / len(values), 2), "count": len(values)}
                for key, values in sorted(categories.items())
            ],
            recent=recent[:8],
        )

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _distribution(rows: Sequence[Grade], size: int = 5) -> list[dict]:
        buckets = [
            {"range": "0-20", "min": 0, "max": 20, "count": 0},
            {"range": "20-40", "min": 20, "max": 40, "count": 0},
            {"range": "40-60", "min": 40, "max": 60, "count": 0},
            {"range": "60-80", "min": 60, "max": 80, "count": 0},
            {"range": "80-100", "min": 80, "max": 101, "count": 0},
        ]
        for grade in rows:
            percentage = grade.percentage
            for bucket in buckets:
                if bucket["min"] <= percentage < bucket["max"]:
                    bucket["count"] += 1
                    break
        return buckets

    @staticmethod
    def _projection(values: Sequence[float], upcoming_weight: float = 20.0) -> float | None:
        if not values:
            return None
        projected = (sum(values) + 70.0 * upcoming_weight / 100) / (1 + upcoming_weight / 100)
        return round(projected, 2)

    @staticmethod
    def _needed_for_pass(values: Sequence[float]) -> float | None:
        if not values:
            return None
        remaining = max(0, 100 - sum(values))
        remaining_count = max(1, 3 - len(values))
        needed = remaining / remaining_count
        return round(needed, 2) if needed > 0 else PASSING_SCORE

    def _sync_exam_status(self, grade: Grade) -> None:
        if grade.exam_id is None:
            return
        from sqlalchemy import select

        exam = self.db.scalars(
            select(Exam).where(Exam.id == grade.exam_id, Exam.user_id == self.user.id)
        ).first()
        if exam is not None and exam.status == ExamStatus.SCHEDULED:
            exam.status = ExamStatus.COMPLETED

    def _to_read(self, grade: Grade) -> GradeRead:
        return GradeRead(
            **{
                "id": grade.id,
                "title": grade.title,
                "course_id": grade.course_id,
                "course": grade.course,
                "exam_id": grade.exam_id,
                "category": grade.category,
                "score": grade.score,
                "max_score": grade.max_score,
                "percentage": grade.percentage,
                "weight": grade.weight,
                "graded_at": grade.graded_at,
                "graded_on_date": grade.graded_on_date,
                "notes": grade.notes,
                "created_at": grade.created_at,
            }
        )


def build_study_focus(grades: Sequence[Grade]) -> list[str]:
    """Topics where the student is weakest — derived from grade categories."""
    buckets: dict[str, list[float]] = {}
    for grade in grades:
        buckets.setdefault(grade.category, []).append(grade.percentage)
    return [
        category
        for category, values in sorted(
            buckets.items(), key=lambda item: sum(item[1]) / len(item[1])
        )
        if sum(values) / len(values) < 80
    ][:5]


def days_until(moment: datetime | None) -> int | None:
    if moment is None:
        return None
    delta = moment - datetime.now(UTC)
    return max(0, delta.days)


def today() -> date:
    return datetime.now(UTC).date()


def week_bounds(reference: date | None = None) -> tuple[datetime, datetime]:
    reference = reference or today()
    start = datetime.combine(reference, datetime.min.time(), tzinfo=UTC) - timedelta(
        days=reference.weekday()
    )
    return start, start + timedelta(days=7)