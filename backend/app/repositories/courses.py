"""Course repository (courses + the enrollments that grant access)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from app.models.academic import Grade
from app.models.course import Course, Enrollment
from app.models.enums import CourseStatus, EnrollmentRole, EnrollmentStatus
from app.repositories.base import BaseRepository


class CourseRepository(BaseRepository[Course]):
    model = Course

    def list_for_user(
        self, user_id: uuid.UUID, *, status: CourseStatus | None = None
    ) -> Sequence[tuple[Course, Enrollment]]:
        statement = (
            select(Course, Enrollment)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(
                Enrollment.user_id == user_id,
                Enrollment.status == EnrollmentStatus.ACTIVE,
            )
            .order_by(Course.semester.is_(None), Course.semester.desc(), Course.name)
        )
        if status is not None:
            statement = statement.where(Course.status == status)
        return self.db.execute(statement).all()

    def get_enrollment(self, user_id: uuid.UUID, course_id: uuid.UUID) -> Enrollment | None:
        return self.db.scalars(
            select(Enrollment).where(
                Enrollment.user_id == user_id, Enrollment.course_id == course_id
            )
        ).first()

    def course_for_user(self, user_id: uuid.UUID, course_id: uuid.UUID) -> Course | None:
        return self.db.scalars(
            select(Course)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(Enrollment.user_id == user_id, Course.id == course_id)
        ).first()

    def enroll(
        self, user_id: uuid.UUID, course_id: uuid.UUID, role: EnrollmentRole = EnrollmentRole.OWNER
    ) -> Enrollment:
        existing = self.get_enrollment(user_id, course_id)
        if existing is not None:
            return existing
        enrollment = Enrollment(user_id=user_id, course_id=course_id, role=role)
        self.db.add(enrollment)
        self.db.flush()
        return enrollment

    def duplicate_code_exists(self, user_id: uuid.UUID, code: str) -> bool:
        alias_course = aliased(Course)
        return (
            self.db.scalar(
                select(func.count(alias_course.id))
                .join(Enrollment, Enrollment.course_id == alias_course.id)
                .where(Enrollment.user_id == user_id, func.upper(alias_course.code) == code.upper())
            )
            or 0
        ) > 0

    def average_grade(self, course_ids: list[uuid.UUID]) -> float | None:
        if not course_ids:
            return None
        rows = self.db.execute(
            select(Grade.score, Grade.max_score).where(Grade.course_id.in_(course_ids))
        ).all()
        percentages = [
            (score / max_score) * 100 for score, max_score in rows if max_score
        ]
        if not percentages:
            return None
        return round(sum(percentages) / len(percentages), 2)

    def user_course_ids(self, user_id: uuid.UUID, *, active_only: bool = True) -> list[uuid.UUID]:
        statement = select(Course.id).join(Enrollment, Enrollment.course_id == Course.id).where(
            Enrollment.user_id == user_id
        )
        if active_only:
            statement = statement.where(Course.status == CourseStatus.ACTIVE)
        return list(self.db.scalars(statement).all())