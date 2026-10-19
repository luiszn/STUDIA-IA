"""Insights: dashboard, calendar, global search and recommendations.

Everything here is derived from real rows in the database — the AI is only used
to phrase recommendations, never to invent academic facts.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.ai.prompts import academic_system_prompt, weak_topics_prompt
from app.ai.registry import resolve_provider
from app.core.logging import get_logger
from app.models.academic import Exam, Grade, Task
from app.models.document import Document, DocumentChunk
from app.models.enums import CourseStatus, Priority, TaskStatus
from app.models.study import Conversation, Recommendation, StudySession
from app.models.user import User
from app.repositories.academic import ExamRepository, GradeRepository, TaskRepository
from app.repositories.courses import CourseRepository
from app.repositories.documents import DocumentRepository
from app.repositories.study import (
    FlashcardRepository,
    RecommendationRepository,
    StudySessionRepository,
)
from app.schemas.academic import CourseGradeSummary
from app.schemas.dashboard import (
    ActivityItem,
    CalendarEvent,
    CalendarResponse,
    DashboardResponse,
    DashboardStats,
    PerformancePoint,
    PerformanceSeries,
    SearchResponse,
    SearchResultItem,
)
from app.schemas.study import RecommendationRead, WeakTopic
from app.services.academic_service import GradeService
from app.services.study_service import StudyService
from app.utils.text import excerpt

logger = get_logger("app.insights")

_DAY_LABELS = {
    0: "lunes",
    1: "martes",
    2: "miércoles",
    3: "jueves",
    4: "viernes",
    5: "sábado",
    6: "domingo",
}


class InsightService:
    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user
        self.tasks = TaskRepository(db)
        self.exams = ExamRepository(db)
        self.grades = GradeRepository(db)
        self.courses = CourseRepository(db)
        self.documents = DocumentRepository(db)
        self.flashcards = FlashcardRepository(db)
        self.sessions = StudySessionRepository(db)
        self.recommendations = RecommendationRepository(db)

    # ----------------------------------------------------------- dashboard
    def dashboard(self) -> DashboardResponse:
        now = datetime.now(UTC)
        # Monday at 00:00, otherwise sessions logged earlier this week are lost.
        week_start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        course_rows = self.courses.list_for_user(self.user.id)
        active_courses = [course for course, _ in course_rows if course.status == CourseStatus.ACTIVE]

        pending = self.tasks.count_by_status(self.user.id, TaskStatus.PENDING) + self.tasks.count_by_status(
            self.user.id, TaskStatus.IN_PROGRESS
        )
        overdue = self.tasks.count_overdue(self.user.id)
        completed = self.tasks.count_by_status(self.user.id, TaskStatus.COMPLETED)
        upcoming = self.exams.upcoming(self.user.id, limit=6)
        next_exam = upcoming[0] if upcoming else None
        overview = GradeService(self.db, self.user).overview()
        study = StudyService(self.db, self.user)

        stats = DashboardStats(
            active_courses=len(active_courses),
            total_courses=len(course_rows),
            pending_tasks=pending,
            overdue_tasks=overdue,
            completed_tasks=completed,
            upcoming_exams=len(upcoming),
            next_exam_in_days=_days_until(next_exam.scheduled_at) if next_exam else None,
            average_grade=overview.overall_average,
            study_minutes_week=self.sessions.minutes_between(self.user.id, week_start, now),
            study_minutes_total=self.sessions.minutes_between(
                self.user.id, now - timedelta(days=365), now + timedelta(days=1)
            ),
            documents=self.documents.count(),
            flashcards=self.flashcards.total_for_user(self.user.id),
            flashcards_due=len(self.flashcards.due(self.user.id)),
            study_streak_days=study.streak_days(),
            daily_goal_minutes=self.user.daily_study_goal_minutes,
        )

        activity = self._upcoming_activity(now)
        recommendation = self._headline_recommendation(now, overview.courses, upcoming, pending, overdue)
        performance = self._performance(now, week_start, overview.courses)

        focus_course = None
        if overview.courses:
            weakest = overview.courses[0]
            focus_course = {
                "course_id": str(weakest.course_id),
                "code": weakest.course_code,
                "name": weakest.course_name,
                "color": weakest.color,
                "average": weakest.average,
                "projected": weakest.projected,
                "required_to_pass": weakest.required_to_pass,
            }

        return DashboardResponse(
            greeting=_greeting(),
            generated_at=now,
            stats=stats,
            upcoming=activity,
            recommendation=recommendation,
            performance=performance,
            focus_course=focus_course,
            quick_actions=QUICK_ACTIONS,
        )

    def _upcoming_activity(self, now: datetime, *, limit: int = 6) -> list[ActivityItem]:
        items: list[ActivityItem] = []

        tasks = self.db.scalars(
            select(Task)
            .where(
                Task.user_id == self.user.id,
                Task.status != TaskStatus.COMPLETED,
                Task.due_at.is_not(None),
                Task.due_at <= now + timedelta(days=14),
            )
            .order_by(Task.due_at)
            .limit(limit)
        ).all()
        course_map = {course.id: course for course, _ in self.courses.list_for_user(self.user.id)}
        for task in tasks:
            course = course_map.get(task.course_id) if task.course_id else None
            items.append(
                ActivityItem(
                    id=str(task.id),
                    kind="task",
                    title=task.title,
                    course_name=course.name if course else None,
                    course_code=course.code if course else None,
                    color=course.color if course else None,
                    date=task.due_at,
                    time_label=_relative_label(task.due_at),
                    priority=task.priority,
                    status=task.status,
                    path=f"/app/tasks?selected={task.id}",
                    is_overdue=task.is_overdue(now),
                )
            )

        for exam in self.exams.upcoming(self.user.id, limit=4):
            course = exam.course
            items.append(
                ActivityItem(
                    id=str(exam.id),
                    kind="exam",
                    title=exam.title,
                    course_name=course.name if course else None,
                    course_code=course.code if course else None,
                    color=course.color if course else None,
                    date=exam.scheduled_at,
                    time_label=_relative_label(exam.scheduled_at),
                    status=exam.status,
                    path=f"/app/calendar?selected={exam.id}",
                )
            )

        sessions = self.db.scalars(
            select(StudySession)
            .where(
                StudySession.user_id == self.user.id,
                StudySession.started_at >= now,
                StudySession.started_at <= now + timedelta(days=7),
            )
            .order_by(StudySession.started_at)
            .limit(3)
        ).all()
        for session in sessions:
            course = session.course
            items.append(
                ActivityItem(
                    id=str(session.id),
                    kind="session",
                    title=session.focus,
                    course_name=course.name if course else None,
                    course_code=course.code if course else None,
                    color=course.color if course else None,
                    date=session.started_at,
                    time_label=_relative_label(session.started_at),
                    path="/app/plan",
                )
            )

        items.sort(key=lambda item: (item.date is None, item.date))
        return items[:limit]

    def _performance(
        self, now: datetime, week_start: datetime, courses: Sequence[CourseGradeSummary]
    ) -> PerformanceSeries:
        study_points: list[PerformancePoint] = []
        for offset in range(6, -1, -1):
            day_start = (week_start - timedelta(days=offset * 7)).date()
            day_end = day_start + timedelta(days=6)
            minutes = int(
                self.db.scalar(
                    select(func.coalesce(func.sum(StudySession.duration_minutes), 0)).where(
                        StudySession.user_id == self.user.id,
                        func.date(StudySession.started_at) >= day_start,
                        func.date(StudySession.started_at) <= day_end,
                    )
                )
                or 0
            )
            study_points.append(PerformancePoint(label=day_start.strftime("%d/%m"), value=minutes))

        grade_points = [
            PerformancePoint(label=summary.course_code, value=summary.average) for summary in courses
        ]
        return PerformanceSeries(
            study_minutes=study_points,
            grades=grade_points,
            by_course=[
                {
                    "course_id": str(summary.course_id),
                    "code": summary.course_code,
                    "name": summary.course_name,
                    "color": summary.color,
                    "average": summary.average,
                    "trend": summary.trend,
                    "count": summary.count,
                }
                for summary in courses
            ],
        )

    # -------------------------------------------------------- recommendations
    def list_recommendations(self) -> list[RecommendationRead]:
        rows = self.recommendations.active_for_user(self.user.id)
        if not rows:
            # Nothing cached yet: derive them from current data so the widget
            # is useful on a first visit instead of showing an empty state.
            self.regenerate_recommendations()
            rows = self.recommendations.active_for_user(self.user.id)
        return [RecommendationRead.model_validate(row) for row in rows]

    def regenerate_recommendations(self) -> list[RecommendationRead]:
        """Deterministic rules over real data, phrased for the student."""
        now = datetime.now(UTC)
        overview = GradeService(self.db, self.user).overview()
        upcoming = self.exams.upcoming(self.user.id, limit=5)
        pending = self.tasks.count_by_status(self.user.id, TaskStatus.PENDING)
        overdue = self.tasks.count_overdue(self.user.id)

        self.db.query(Recommendation).filter(
            Recommendation.user_id == self.user.id,
            Recommendation.is_dismissed.is_(False),
        ).delete(synchronize_session=False)

        drafts: list[dict] = []

        if upcoming:
            exam = upcoming[0]
            days = _days_until(exam.scheduled_at) or 0
            course_code = exam.course.code if exam.course else "tu curso"
            if days <= 3:
                drafts.append(
                    {
                        "kind": "upcoming_exam",
                        "title": f"{exam.title} en {days} día(s)",
                        "message": (
                            f"Tienes {exam.title} de {course_code} en {days} días. "
                            f"Reserva hoy una sesión de {min(90, self.user.daily_study_goal_minutes)} minutos "
                            "para repasar los temas más evaluados."
                        ),
                        "priority": Priority.URGENT if days <= 1 else Priority.HIGH,
                        "score": 0.95 - days * 0.03,
                        "cta_label": "Crear plan de estudio",
                        "cta_path": f"/app/plan?course={exam.course_id}",
                        "course_id": exam.course_id,
                        "evidence": {"exam": exam.title, "date": exam.scheduled_at.isoformat()},
                        "expires_at": exam.scheduled_at,
                    }
                )

        if overdue:
            drafts.append(
                {
                    "kind": "priority_task",
                    "title": f"{overdue} tarea(s) vencida(s)",
                    "message": (
                        f"Tienes {overdue} tarea(s) con fecha limite superada y {pending} pendiente(s). "
                        "Resuelve primero la de mayor prioridad o reprograma la que ya no Cabe hoy."
                    ),
                    "priority": Priority.HIGH,
                    "score": 0.9,
                    "cta_label": "Ver tareas",
                    "cta_path": "/app/tasks",
                    "evidence": {"overdue": overdue, "pending": pending},
                    "expires_at": now + timedelta(days=7),
                }
            )

        for summary in overview.courses[:2]:
            if summary.average < 70:
                drafts.append(
                    {
                        "kind": "weak_topic",
                        "title": f"{summary.course_code} necesita refuerzo",
                        "message": (
                            f"Tu promedio en {summary.course_name} es {summary.average}%. "
                            + (
                                f"Necesitas aproximadamente {summary.required_to_pass}% en las próximas notas "
                                "para alcanzar el 60%."
                                if summary.required_to_pass
                                else "Refuerza los temas de menor nota."
                            )
                        ),
                        "priority": Priority.HIGH,
                        "score": 0.85 - summary.average / 500,
                        "cta_label": "Practicar con IA",
                        "cta_path": f"/app/ai?course={summary.course_id}",
                        "course_id": summary.course_id,
                        "evidence": {
                            "average": summary.average,
                            "lowest": summary.lowest,
                            "count": summary.count,
                        },
                        "expires_at": now + timedelta(days=14),
                    }
                )

        due_cards = len(self.flashcards.due(self.user.id))
        if due_cards >= 5:
            drafts.append(
                {
                    "kind": "study_habit",
                    "title": f"{due_cards} flashcards te esperan",
                    "message": (
                        f"Tienes {due_cards} tarjetas pendientes de repaso. "
                        "Un repaso de 15 minutos mantiene la retención alta antes del examen."
                    ),
                    "priority": Priority.MEDIUM,
                    "score": 0.6,
                    "cta_label": "Estudiar flashcards",
                    "cta_path": "/app/flashcards?mode=review",
                    "evidence": {"due": due_cards},
                    "expires_at": now + timedelta(days=3),
                }
            )

        week_minutes = self.sessions.minutes_between(
            self.user.id, now - timedelta(days=now.weekday()), now
        )
        goal = max(30, self.user.daily_study_goal_minutes * 3)
        # Only nudge once the student is actually studying; a brand new account
        # has no history to compare against and would only see noise.
        has_history = self.sessions.total_minutes(self.user.id) > 0 or pending > 0
        if has_history and week_minutes < goal // 2:
            drafts.append(
                {
                    "kind": "workload_balance",
                    "title": "Ritmo de estudio bajo esta semana",
                    "message": (
                        f"Llevas {week_minutes} minutos esta semana y tu objetivo semanal es "
                        f"{goal} minutos. Prueba una sesión de 25 minutos con temporizador hoy."
                    ),
                    "priority": Priority.MEDIUM,
                    "score": 0.55,
                    "cta_label": "Registrar sesión",
                    "cta_path": "/app/plan",
                    "evidence": {"week_minutes": week_minutes, "goal": goal},
                    "expires_at": now + timedelta(days=5),
                }
            )

        for draft in drafts:
            self.db.add(Recommendation(user_id=self.user.id, **draft))
        self.db.commit()
        # Read the rows directly: calling list_recommendations() here would
        # recurse when no rule matches (empty account).
        self.db.expire_all()
        return [
            RecommendationRead.model_validate(row)
            for row in self.recommendations.active_for_user(self.user.id)
        ]

    def mark_recommendation(self, recommendation_id: uuid.UUID, *, read: bool, dismissed: bool) -> RecommendationRead:
        from app.core.errors import NotFoundError

        row = self.db.scalars(
            select(Recommendation).where(
                Recommendation.id == recommendation_id, Recommendation.user_id == self.user.id
            )
        ).first()
        if row is None:
            raise NotFoundError("That recommendation does not exist.")
        row.is_read = read
        row.is_dismissed = dismissed
        self.db.commit()
        self.db.refresh(row)
        return RecommendationRead.model_validate(row)

    def _headline_recommendation(
        self,
        now: datetime,
        courses: Sequence[CourseGradeSummary],
        upcoming: Sequence[Exam],
        pending: int,
        overdue: int,
    ) -> RecommendationRead | None:
        active = self.recommendations.active_for_user(self.user.id, limit=1)
        if active:
            return RecommendationRead.model_validate(active[0])
        fresh = self.regenerate_recommendations()
        return fresh[0] if fresh else None

    # ------------------------------------------------------------ calendar
    def calendar(self, start: date, end: date) -> CalendarResponse:
        events: list[CalendarEvent] = []
        start_dt = datetime.combine(start, datetime.min.time(), tzinfo=UTC)
        end_dt = datetime.combine(end, datetime.max.time(), tzinfo=UTC)
        course_map = {course.id: course for course, _ in self.courses.list_for_user(self.user.id)}

        for task in self.db.scalars(
            select(Task).where(
                Task.user_id == self.user.id,
                Task.due_at.is_not(None),
                Task.due_at >= start_dt,
                Task.due_at <= end_dt,
            )
        ).all():
            course = course_map.get(task.course_id) if task.course_id else None
            events.append(
                CalendarEvent(
                    id=str(task.id),
                    kind="task",
                    title=task.title,
                    course_name=course.name if course else None,
                    color=course.color if course else None,
                    date=task.due_at.date(),
                    time=task.due_at.strftime("%H:%M"),
                    priority=task.priority,
                    status=task.status,
                    path=f"/app/tasks?selected={task.id}",
                    meta={"estimated_minutes": task.estimated_minutes},
                )
            )

        for exam in self.exams.between(self.user.id, start_dt, end_dt):
            course = exam.course
            events.append(
                CalendarEvent(
                    id=str(exam.id),
                    kind="exam",
                    title=exam.title,
                    course_name=course.name if course else None,
                    color=course.color if course else None,
                    date=exam.scheduled_at.date(),
                    time=exam.scheduled_at.strftime("%H:%M"),
                    status=exam.status,
                    path=f"/app/calendar?selected={exam.id}",
                    meta={
                        "duration_minutes": exam.duration_minutes,
                        "location": exam.location,
                        "exam_type": exam.exam_type,
                    },
                )
            )

        for session in self.db.scalars(
            select(StudySession).where(
                StudySession.user_id == self.user.id,
                StudySession.started_at >= start_dt,
                StudySession.started_at <= end_dt,
            )
        ).all():
            course = session.course
            events.append(
                CalendarEvent(
                    id=str(session.id),
                    kind="session",
                    title=session.focus,
                    course_name=course.name if course else None,
                    color=course.color if course else None,
                    date=session.started_at.date(),
                    time=session.started_at.strftime("%H:%M"),
                    path="/app/plan",
                    meta={"duration_minutes": session.duration_minutes},
                )
            )

        events.sort(key=lambda event: (event.date, event.time or ""))
        return CalendarResponse(start=start, end=end, events=events)

    # -------------------------------------------------------------- search
    def search(self, query: str, *, limit: int = 6) -> SearchResponse:
        term = query.strip()
        results: list[SearchResultItem] = []
        if len(term) < 2:
            return SearchResponse(query=term, total=0, results=[])

        pattern = f"%{term}%"
        seen_documents: set[uuid.UUID] = set()

        for course, _ in self.courses.list_for_user(self.user.id):
            if term.lower() in course.name.lower() or term.lower() in course.code.lower():
                results.append(
                    SearchResultItem(
                        id=course.id,
                        type="course",
                        title=course.name,
                        subtitle=f"{course.code}{f' · {course.professor}' if course.professor else ''}",
                        path=f"/app/courses/{course.id}",
                        meta={"color": course.color},
                    )
                )

        for task in self.db.scalars(
            select(Task)
            .where(Task.user_id == self.user.id, or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))
            .limit(limit)
        ).all():
            results.append(
                SearchResultItem(
                    id=task.id,
                    type="task",
                    title=task.title,
                    subtitle=task.course.name if task.course else "Tarea sin curso",
                    path=f"/app/tasks?selected={task.id}",
                    meta={"status": task.status},
                )
            )

        for document in self.documents.list_for_user(self.user.id, search=term)[:limit]:
            results.append(
                SearchResultItem(
                    id=document.id,
                    type="document",
                    title=document.title,
                    subtitle=document.filename,
                    path=f"/app/documents?selected={document.id}",
                    meta={"status": document.status, "extension": document.extension},
                )
            )
            seen_documents.add(document.id)

        results.extend(self._search_document_content(pattern, seen_documents, limit))

        for card in self.db.scalars(
            self.flashcards.filtered(self.user.id, search=term).limit(limit)
        ).all():
            results.append(
                SearchResultItem(
                    id=card.id,
                    type="flashcard",
                    title=card.front,
                    subtitle=f"{card.deck} · {card.back[:60]}",
                    path=f"/app/flashcards?card={card.id}",
                    meta={"deck": card.deck},
                )
            )

        for conversation in self.db.scalars(
            select(Conversation)
            .where(Conversation.user_id == self.user.id, Conversation.title.ilike(pattern))
            .limit(limit)
        ).all():
            results.append(
                SearchResultItem(
                    id=conversation.id,
                    type="conversation",
                    title=conversation.title,
                    subtitle=f"{conversation.message_count} mensajes",
                    path=f"/app/ai?conversation={conversation.id}",
                )
            )

        for exam in self.db.scalars(
            select(Exam).where(Exam.user_id == self.user.id, Exam.title.ilike(pattern)).limit(limit)
        ).all():
            results.append(
                SearchResultItem(
                    id=exam.id,
                    type="exam",
                    title=exam.title,
                    subtitle=exam.course.name if exam.course else "Evaluación",
                    path=f"/app/calendar?selected={exam.id}",
                    meta={"scheduled_at": exam.scheduled_at.isoformat()},
                )
            )

        for grade in self.db.scalars(
            select(Grade).where(Grade.user_id == self.user.id, Grade.title.ilike(pattern)).limit(limit)
        ).all():
            results.append(
                SearchResultItem(
                    id=grade.id,
                    type="grade",
                    title=grade.title,
                    subtitle=f"{grade.percentage:.1f}% · {grade.course.name if grade.course else ''}",
                    path="/app/performance",
                    meta={"percentage": grade.percentage},
                )
            )

        groups: dict[str, int] = {}
        for item in results:
            groups[item.type] = groups.get(item.type, 0) + 1
        return SearchResponse(query=term, total=len(results), results=results, groups=groups)

    def _search_document_content(
        self, pattern: str, seen: set[uuid.UUID], limit: int
    ) -> list[SearchResultItem]:
        """Match the extracted text so a document is findable by its content."""
        if len(seen) >= limit:
            return []

        document_ids = [
            document_id
            for (document_id,) in self.db.execute(
                select(DocumentChunk.document_id)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(Document.user_id == self.user.id, DocumentChunk.content.ilike(pattern))
                .distinct()
                .limit(limit)
            ).all()
            if document_id not in seen
        ]
        if not document_ids:
            return []

        documents = self.documents.get_many_owned(self.user.id, document_ids)
        return [
            SearchResultItem(
                id=document.id,
                type="document",
                title=document.title,
                subtitle=document.filename,
                path=f"/app/documents?selected={document.id}",
                meta={"status": document.status, "extension": document.extension},
            )
            for document in documents
        ]

    # ---------------------------------------------------------- weak topics
    async def weak_topics(self) -> list[WeakTopic]:
        """Rule based first, AI phrasing second — never the other way round."""
        overview = GradeService(self.db, self.user).overview()
        topics: list[WeakTopic] = []

        for summary in overview.courses:
            if summary.average >= 75:
                continue
            confidence = min(0.95, max(0.4, (75 - summary.average) / 50 + 0.3))
            evidence = [f"Promedio {summary.average}% en {summary.count} evaluaciones"]
            if summary.lowest < summary.average - 10:
                evidence.append(f"La peor nota fue {summary.lowest}%")
            if summary.required_to_pass:
                evidence.append(f"Necesitas ~{summary.required_to_pass}% para aprobar")
            topics.append(
                WeakTopic(
                    topic=summary.course_name,
                    course_id=summary.course_id,
                    course_name=summary.course_code,
                    confidence=round(confidence, 2),
                    evidence=evidence,
                    suggested_action="Genera preguntas de práctica y repasa con flashcards.",
                )
            )

        unread = self.documents.list_for_user(self.user.id, status="ready")
        if unread:
            try:
                resolved = await resolve_provider()
                completion = await resolved.provider.complete_text(
                    weak_topics_prompt(
                        context=excerpt(" ".join(document.title for document in unread), 1500),
                        student_data=f"- Documentos indexados: {len(unread)}",
                    ),
                    system=academic_system_prompt(),
                    temperature=0.2,
                    max_tokens=400,
                )
                from app.ai.rag.parsing import ensure_list, extract_json

                try:
                    parsed = extract_json(completion.content)
                except ValueError:
                    parsed = {}
                for item in ensure_list(parsed, "topics")[:3]:
                    name = str(item.get("topic") or "").strip()
                    if not name:
                        continue
                    topics.append(
                        WeakTopic(
                            topic=name,
                            confidence=float(item.get("confidence") or 0.5),
                            evidence=[str(value)[:140] for value in (item.get("evidence") or [])][:3],
                            suggested_action="Pide un resumen del material sobre este tema.",
                        )
                    )
            except Exception:  # noqa: BLE001 - weak topics degrade gracefully
                logger.debug("AI weak-topic pass failed", exc_info=True)

        topics.sort(key=lambda item: -item.confidence)
        return topics[:6]


# ---------------------------------------------------------------- helpers
QUICK_ACTIONS = [
    {"id": "summarize", "label": "Resumir documento", "path": "/app/documents?action=summarize", "icon": "FileText"},
    {"id": "questions", "label": "Crear preguntas", "path": "/app/questions", "icon": "ListChecks"},
    {"id": "flashcards", "label": "Crear flashcards", "path": "/app/flashcards?action=generate", "icon": "Layers"},
    {"id": "explain", "label": "Explicarme un tema", "path": "/app/ai?mode=explain", "icon": "Sparkles"},
    {"id": "plan", "label": "Crear plan de estudio", "path": "/app/plan", "icon": "CalendarRange"},
]


def _greeting() -> str:
    hour = datetime.now(UTC).hour
    if hour < 12:
        return "Buenos días"
    if hour < 19:
        return "Buenas tardes"
    return "Buenas noches"


def _days_until(moment: datetime) -> int:
    """Calendar days left, so an exam in 4 days reads as 4 (not 3)."""
    today = datetime.now(UTC).date()
    return max(0, (moment.date() - today).days)


def _relative_label(moment: datetime) -> str:
    delta = moment - datetime.now(UTC)
    days = delta.days
    if days < 0:
        overdue = abs(days)
        return f"Vencida hace {overdue} día(s)" if overdue > 1 else "Vencida hoy"
    if days == 0:
        hours = max(0, delta.seconds // 3600)
        return "Hoy" if hours <= 12 else f"Mañana {_DAY_LABELS[(datetime.now(UTC) + timedelta(days=1)).weekday()]}"
    if days == 1:
        return "Mañana"
    if days <= 7:
        return f"{_DAY_LABELS[(moment).weekday()].capitalize()} ({days} días)"
    return moment.strftime("%d/%m/%Y")