"""Course service — ownership, stats and course-level aggregation."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.models.academic import Exam, Grade, Task
from app.models.course import Course, Enrollment
from app.models.document import Document
from app.models.enums import CourseStatus, EnrollmentRole, TaskStatus
from app.models.study import Flashcard, StudySession
from app.models.user import User
from app.repositories.academic import ExamRepository, TaskRepository
from app.repositories.courses import CourseRepository
from app.schemas.course import CourseCreate, CourseRead, CourseStats, CourseUpdate


class CourseService:
    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user
        self.courses = CourseRepository(db)
        self.tasks = TaskRepository(db)
        self.exams = ExamRepository(db)

    # ---------------------------------------------------------------- list
    def list(self, status: CourseStatus | None = None) -> list[CourseRead]:
        rows = self.courses.list_for_user(self.user.id, status=status)
        return [self._to_read(course, enrollment) for course, enrollment in rows]

    def get(self, course_id: uuid.UUID) -> CourseRead:
        course, enrollment = self._require(course_id)
        return self._to_read(course, enrollment)

    # -------------------------------------------------------------- mutate
    def create(self, payload: CourseCreate) -> CourseRead:
        if self.courses.duplicate_code_exists(self.user.id, payload.code):
            raise ConflictError(
                f"You already have a course with the code {payload.code}.", code="duplicate_course"
            )
        course = Course(**payload.model_dump())
        self.db.add(course)
        self.db.flush()
        enrollment = self.courses.enroll(self.user.id, course.id, EnrollmentRole.OWNER)
        self.db.commit()
        self.db.refresh(course)
        return self._to_read(course, enrollment)

    def update(self, course_id: uuid.UUID, payload: CourseUpdate) -> CourseRead:
        course, enrollment = self._require(course_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(course, field, value)
        self.db.commit()
        self.db.refresh(course)
        return self._to_read(course, enrollment)

    def delete(self, course_id: uuid.UUID) -> None:
        course, enrollment = self._require(course_id)
        if not enrollment.is_owner:
            raise PermissionDeniedError("Only the course owner can delete it.")
        # Detach dependent rows that must survive the course.
        for document in self.db.scalars(
            select(Document).where(Document.course_id == course.id)
        ).all():
            document.course_id = None
        for grade in self.db.scalars(select(Grade).where(Grade.course_id == course.id)).all():
            grade.course_id = course.id  # grades are historical: keep the row
        self.db.delete(course)
        self.db.commit()

    # --------------------------------------------------------------- stats
    def stats(self, course_id: uuid.UUID) -> CourseStats:
        course, _ = self._require(course_id)
        total_tasks = self.tasks.count(Task.course_id == course_id)
        completed = self.tasks.count(
            Task.course_id == course_id, Task.status == TaskStatus.COMPLETED
        )
        overdue = int(
            self.db.scalar(
                select(func.count(Task.id)).where(
                    Task.course_id == course_id,
                    Task.status != TaskStatus.COMPLETED,
                    Task.due_at.is_not(None),
                    Task.due_at < func.now(),
                )
            )
            or 0
        )
        upcoming_exams = int(
            self.db.scalar(
                select(func.count(Exam.id)).where(
                    Exam.course_id == course_id, Exam.status == "scheduled"
                )
            )
            or 0
        )
        percentages = [
            (row.score / row.max_score) * 100
            for row in self.db.execute(
                select(Grade.score, Grade.max_score).where(Grade.course_id == course_id)
            ).all()
            if row.max_score
        ]
        study_minutes = int(
            self.db.scalar(
                select(func.coalesce(func.sum(StudySession.duration_minutes), 0)).where(
                    StudySession.course_id == course_id
                )
            )
            or 0
        )
        return CourseStats(
            total_tasks=total_tasks,
            completed_tasks=completed,
            overdue_tasks=overdue,
            upcoming_exams=upcoming_exams,
            average_grade=round(sum(percentages) / len(percentages), 2) if percentages else None,
            highest_grade=round(max(percentages), 2) if percentages else None,
            documents=self._count(Document, course_id),
            flashcards=self._count(Flashcard, course_id),
            study_minutes=study_minutes,
        )

    # ------------------------------------------------------------- helpers
    def require_course(self, course_id: uuid.UUID) -> Course:
        course, _ = self._require(course_id)
        return course

    def course_ids(self, *, active_only: bool = True) -> list[uuid.UUID]:
        return self.courses.user_course_ids(self.user.id, active_only=active_only)

    def course_names(self) -> list[str]:
        rows = self.courses.list_for_user(self.user.id)
        return [f"{course.code} — {course.name}" for course, _ in rows]

    def _require(self, course_id: uuid.UUID) -> tuple[Course, Enrollment]:
        enrollment = self.courses.get_enrollment(self.user.id, course_id)
        if enrollment is None or enrollment.status != "active":
            raise NotFoundError("That course does not exist in your account.", code="course_not_found")
        course = self.courses.get(course_id)
        if course is None:
            raise NotFoundError("That course does not exist in your account.", code="course_not_found")
        return course, enrollment

    def _count(self, model: type, course_id: uuid.UUID) -> int:
        return int(
            self.db.scalar(select(func.count(model.id)).where(model.course_id == course_id)) or 0
        )

    def _to_read(self, course: Course, enrollment: Enrollment) -> CourseRead:
        stats = self.stats(course.id)
        return CourseRead(
            **{
                "id": course.id,
                "code": course.code,
                "name": course.name,
                "description": course.description,
                "professor": course.professor,
                "credits": course.credits,
                "semester": course.semester,
                "academic_year": course.academic_year,
                "color": course.color,
                "status": course.status,
                "created_at": course.created_at,
                "updated_at": course.updated_at,
                "role": enrollment.role,
                "task_count": stats.total_tasks,
                "pending_task_count": stats.total_tasks - stats.completed_tasks,
                "document_count": stats.documents,
                "flashcard_count": stats.flashcards,
                "exam_count": stats.upcoming_exams,
                "average_grade": stats.average_grade,
            }
        )


def course_map(courses: Sequence[Course]) -> dict[uuid.UUID, Course]:
    return {course.id: course for course in courses}