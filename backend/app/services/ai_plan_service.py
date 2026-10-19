"""AI study plan generation grounded in the student's real academic data."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.ai.prompts import STRICT_JSON_RULE, academic_system_prompt, study_plan_prompt
from app.ai.rag.parsing import coerce_int, ensure_list, extract_json
from app.ai.rag.retriever import Retriever
from app.ai.registry import resolve_provider
from app.core.errors import ValidationError
from app.core.logging import get_logger
from app.models.course import Course
from app.models.enums import StudyPlanStatus
from app.models.study import StudyPlan
from app.models.user import User
from app.repositories.courses import CourseRepository
from app.repositories.documents import DocumentRepository
from app.repositories.study import StudyPlanRepository
from app.schemas.academic import ExamRead
from app.schemas.study import StudyPlanCreate, StudyPlanDay, StudyPlanRead
from app.services.study_service import plan_to_read
from app.utils.text import excerpt

logger = get_logger("app.ai.plans")

MAX_DAYS = 60
MAX_DAILY_MINUTES = 480


class StudyPlanService:
    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user
        self.plans = StudyPlanRepository(db)
        self.courses = CourseRepository(db)
        self.documents = DocumentRepository(db)

    async def generate(self, payload: StudyPlanCreate) -> StudyPlanRead:
        resolved = await resolve_provider()
        provider = resolved.provider

        course, exam, exam_date = self._resolve_target(payload)
        total_days = min(payload.total_days, MAX_DAYS)
        daily_minutes = min(payload.daily_minutes, MAX_DAILY_MINUTES)
        weak_topics = self._weak_topics(course.id if course else None)

        documents = (
            self.documents.get_many_owned(self.user.id, payload.document_ids)
            if payload.document_ids
            else []
        )
        if not documents and course is not None:
            documents = [
                document
                for document in self.documents.list_for_user(self.user.id, course_id=course.id)
                if document.status == "ready"
            ][:5]

        context = await Retriever(self.db, provider, self.user.id).retrieve(
            " ".join(payload.focus_topics) or (course.name if course else "study plan"),
            document_ids=[document.id for document in documents] or None,
            top_k=10,
            min_score=0.0,
        )

        prompt = study_plan_prompt(
            course_name=course.name if course else "General",
            exam_date=exam_date.strftime("%Y-%m-%d") if exam_date else None,
            total_days=total_days,
            daily_minutes=daily_minutes,
            level=payload.level,
            focus_topics=payload.focus_topics or weak_topics,
            weak_topics=weak_topics if payload.use_weak_topics else [],
            context=context.context_text,
            student_data=self._student_data(),
            exam_topics=exam.topics if exam else None,
        )
        completion = await provider.complete_text(
            prompt,
            system=f"{academic_system_prompt()}\n{STRICT_JSON_RULE}",
            temperature=0.35,
            json_mode=True,
            max_tokens=3000,
        )

        days = _normalize_days(completion.content, total_days=total_days, daily_minutes=daily_minutes)
        if not days:
            raise ValidationError(
                "The AI did not return a usable plan. Please try again.",
                code="empty_plan",
            )
        _assign_day_dates(days, exam_date)

        plan = StudyPlan(
            user_id=self.user.id,
            course_id=payload.course_id or (course.id if course else None),
            exam_id=payload.exam_id or (exam.id if exam else None),
            exam_date=exam_date,
            title=(payload.title or _title(completion.content) or f"Plan de estudio — {course.name if course else 'General'}")[:180],
            level=payload.level,
            daily_minutes=daily_minutes,
            total_days=len(days),
            total_minutes=sum(day.theory_minutes + day.practice_minutes + day.review_minutes for day in days),
            status=StudyPlanStatus.DRAFT,
            days=[day.model_dump() for day in days],
            weak_topics=payload.focus_topics or weak_topics,
            rationale=_rationale(
                completion.content,
                days=days,
                daily_minutes=daily_minutes,
                weak_topics=payload.focus_topics or weak_topics,
            ),
            provider=completion.provider,
            model=completion.model,
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return self._to_read(plan)

    def get(self, plan_id: uuid.UUID) -> StudyPlanRead:
        from app.services.study_service import StudyService

        return StudyService(self.db, self.user).get_plan(plan_id)

    # ------------------------------------------------------------- helpers
    def _resolve_target(
        self, payload: StudyPlanCreate
    ) -> tuple[Course | None, ExamRead | None, datetime | None]:
        course: Course | None = None
        if payload.course_id is not None:
            course = self.courses.course_for_user(self.user.id, payload.course_id)
            if course is None:
                raise ValidationError("You are not enrolled in that course.", code="course_not_accessible")

        exam: ExamRead | None = None
        exam_date = payload.exam_date
        if payload.exam_id is not None:
            from app.services.academic_service import ExamService

            exam = ExamService(self.db, self.user).get(payload.exam_id)
            exam_date = exam_date or exam.scheduled_at
            if course is None and exam.course_id:
                course = self.courses.course_for_user(self.user.id, exam.course_id)

        if exam_date is None and course is not None:
            from sqlalchemy import select

            from app.models.academic import Exam

            next_exam = self.db.scalars(
                select(Exam)
                .where(Exam.course_id == course.id, Exam.scheduled_at >= datetime.now(UTC))
                .order_by(Exam.scheduled_at)
                .limit(1)
            ).first()
            exam_date = next_exam.scheduled_at if next_exam else None

        return course, exam, exam_date

    def _weak_topics(self, course_id: uuid.UUID | None) -> list[str]:
        """Weakest courses (and low-scoring categories) as study priorities."""
        from sqlalchemy import select

        from app.models.academic import Grade

        statement = select(Grade).where(Grade.user_id == self.user.id)
        if course_id is not None:
            statement = statement.where(Grade.course_id == course_id)
        grades = list(self.db.scalars(statement).all())
        if not grades:
            return []

        topics: list[str] = []
        by_category: dict[str, list[float]] = {}
        for grade in grades:
            by_category.setdefault(grade.category, []).append(grade.percentage)
        for category, values in sorted(
            by_category.items(), key=lambda item: sum(item[1]) / len(item[1])
        ):
            if sum(values) / len(values) < 80:
                topics.append(category)

        if course_id is None:
            courses = {course.id: course for course, _ in self.courses.list_for_user(self.user.id)}
            averages: dict[uuid.UUID, list[float]] = {}
            for grade in grades:
                averages.setdefault(grade.course_id, []).append(grade.percentage)
            weakest = sorted(
                averages.items(), key=lambda item: sum(item[1]) / len(item[1])
            )[:2]
            for course_id_value, values in weakest:
                if sum(values) / len(values) < 75:
                    course = courses.get(course_id_value)
                    if course:
                        topics.append(course.code)
        return topics[:5]

    def _student_data(self) -> str:
        from app.services.academic_service import GradeService

        overview = GradeService(self.db, self.user).overview()

        return (
            "Datos reales del estudiante (base de datos de STUDIA AI):\n"
            f"- Promedio: {overview.overall_average if overview.overall_average is not None else 'sin notas'}\n"
            f"- Cursos con menor promedio: {[item.course_code for item in overview.courses[-3:]]}\n"
            f"- Total de cursos: {len(overview.courses)}"
        )

    def _to_read(self, plan: StudyPlan) -> StudyPlanRead:
        return plan_to_read(plan)


# ---------------------------------------------------------------- helpers
def _safe_json(text: str) -> Any:
    try:
        return extract_json(text)
    except ValueError:
        logger.warning("Plan JSON parse failed: %s", excerpt(text, 200))
        return {}


def _normalize_days(text: str, *, total_days: int, daily_minutes: int) -> list[StudyPlanDay]:
    parsed = _safe_json(text)
    days: list[StudyPlanDay] = []
    for index, item in enumerate(ensure_list(parsed, "days"), start=1):
        theory = coerce_int(item.get("theory_minutes"), int(daily_minutes * 0.5))
        practice = coerce_int(item.get("practice_minutes"), int(daily_minutes * 0.3))
        review = coerce_int(item.get("review_minutes"), max(10, daily_minutes - theory - practice))
        total = theory + practice + review
        if total <= 0:
            theory, practice, review = daily_minutes // 2, daily_minutes // 3, daily_minutes - daily_minutes // 2 - daily_minutes // 3
        elif total != daily_minutes:
            # Normalise so the plan always matches the requested daily budget.
            scale = daily_minutes / total
            theory = max(10, round(theory * scale))
            practice = max(5, round(practice * scale))
            review = max(5, daily_minutes - theory - practice)
        days.append(
            StudyPlanDay(
                day=coerce_int(item.get("day"), index),
                title=str(item.get("title") or f"Sesión {index}")[:180],
                focus=str(item.get("focus") or item.get("title") or "Repaso")[:180],
                theory_minutes=theory,
                practice_minutes=practice,
                review_minutes=review,
                objectives=[str(value)[:220] for value in (item.get("objectives") or [])][:6],
                resources=[str(value)[:220] for value in (item.get("resources") or [])][:6],
            )
        )
    if not days:
        return []
    days.sort(key=lambda day: day.day)
    return days[:total_days]


def _assign_day_dates(days: list[StudyPlanDay], exam_date: datetime | None) -> None:
    """Anchor the plan on the calendar so the UI can render it.

    With a known exam date the plan finishes the day before it, otherwise it
    starts today. Days that already carry a valid date are left untouched.
    """
    if not days:
        return
    today = datetime.now(UTC).date()
    start = exam_date.date() - timedelta(days=len(days)) if exam_date is not None else today
    if start < today:
        start = today
    for index, day in enumerate(days):
        if day.date:
            continue
        day.date = (start + timedelta(days=index)).isoformat()


def _rationale(text: str, *, days: list[StudyPlanDay], daily_minutes: int, weak_topics: list[str]) -> str:
    parsed = _safe_json(text)
    if isinstance(parsed, dict) and parsed.get("rationale"):
        return excerpt(str(parsed["rationale"]), 1200)
    # The local provider does not write a rationale, so describe the shape of
    # the plan instead of leaving the student without any explanation.
    total = sum(day.theory_minutes + day.practice_minutes + day.review_minutes for day in days)
    hours = round(total / 60, 1)
    parts = [
        f"Plan de {len(days)} días a {daily_minutes} minutos diarios ({hours} horas en total), "
        "combinando teoría, práctica y repaso activo."
    ]
    if weak_topics:
        topics = ", ".join(weak_topics[:5])
        parts.append(f"Se priorizan los temas con menor desempeño: {topics}.")
    else:
        parts.append("El orden va de lo general a lo específico, con repaso espaciado al final de cada día.")
    return " ".join(parts)


def _title(text: str) -> str | None:
    parsed = _safe_json(text)
    if isinstance(parsed, dict) and parsed.get("title"):
        return str(parsed["title"])[:180]
    return None


def default_days(total_days: int, daily_minutes: int) -> int:
    return max(1, min(total_days, 60))


def next_exam_window(days: int) -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    return now, now + timedelta(days=days)