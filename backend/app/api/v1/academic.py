"""Task and exam endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Paging
from app.models.enums import ExamStatus, Priority, TaskStatus
from app.schemas.academic import ExamCreate, ExamRead, ExamUpdate, TaskCreate, TaskRead, TaskUpdate
from app.schemas.common import MessageResponse, Page, PageMeta
from app.services.academic_service import ExamService, TaskService

tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])
exams_router = APIRouter(prefix="/exams", tags=["exams"])


# ------------------------------------------------------------------- tasks
@tasks_router.get("", response_model=Page[TaskRead], summary="List tasks")
def list_tasks(
    user: CurrentUser,
    db: DbSession,
    paging: Paging,
    task_status: TaskStatus | None = Query(default=None, alias="status"),
    priority: Priority | None = None,
    course_id: uuid.UUID | None = None,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
    search: str | None = None,
) -> Page[TaskRead]:
    items, total = TaskService(db, user).list(
        status=task_status,
        priority=priority,
        course_id=course_id,
        due_before=due_before,
        due_after=due_after,
        search=search,
        limit=paging.limit,
        offset=paging.offset,
    )
    return Page[TaskRead](
        items=items,
        meta=PageMeta(
            total=total,
            limit=paging.limit,
            offset=paging.offset,
            has_more=paging.offset + len(items) < total,
        ),
    )


@tasks_router.post(
    "", response_model=TaskRead, status_code=status.HTTP_201_CREATED, summary="Create a task"
)
def create_task(payload: TaskCreate, user: CurrentUser, db: DbSession) -> TaskRead:
    return TaskService(db, user).create(payload)


@tasks_router.get("/{task_id}", response_model=TaskRead, summary="Get one task")
def get_task(task_id: uuid.UUID, user: CurrentUser, db: DbSession) -> TaskRead:
    return TaskService(db, user).get(task_id)


@tasks_router.patch("/{task_id}", response_model=TaskRead, summary="Update a task")
def update_task(
    task_id: uuid.UUID, payload: TaskUpdate, user: CurrentUser, db: DbSession
) -> TaskRead:
    return TaskService(db, user).update(task_id, payload)


@tasks_router.post("/{task_id}/toggle", response_model=TaskRead, summary="Complete / reopen a task")
def toggle_task(task_id: uuid.UUID, user: CurrentUser, db: DbSession) -> TaskRead:
    return TaskService(db, user).toggle(task_id)


@tasks_router.delete("/{task_id}", response_model=MessageResponse, summary="Delete a task")
def delete_task(task_id: uuid.UUID, user: CurrentUser, db: DbSession) -> MessageResponse:
    TaskService(db, user).delete(task_id)
    return MessageResponse(message="Task deleted.")


# ------------------------------------------------------------------- exams
@exams_router.get("", response_model=Page[ExamRead], summary="List exams")
def list_exams(
    user: CurrentUser,
    db: DbSession,
    paging: Paging,
    course_id: uuid.UUID | None = None,
    exam_status: ExamStatus | None = Query(default=None, alias="status"),
    upcoming_only: bool = False,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> Page[ExamRead]:
    items, total = ExamService(db, user).list(
        course_id=course_id,
        status=exam_status,
        upcoming_only=upcoming_only,
        from_date=from_date,
        to_date=to_date,
        limit=paging.limit,
        offset=paging.offset,
    )
    return Page[ExamRead](
        items=items,
        meta=PageMeta(
            total=total,
            limit=paging.limit,
            offset=paging.offset,
            has_more=paging.offset + len(items) < total,
        ),
    )


@exams_router.post(
    "", response_model=ExamRead, status_code=status.HTTP_201_CREATED, summary="Create an exam"
)
def create_exam(payload: ExamCreate, user: CurrentUser, db: DbSession) -> ExamRead:
    return ExamService(db, user).create(payload)


@exams_router.get("/{exam_id}", response_model=ExamRead, summary="Get one exam")
def get_exam(exam_id: uuid.UUID, user: CurrentUser, db: DbSession) -> ExamRead:
    return ExamService(db, user).get(exam_id)


@exams_router.patch("/{exam_id}", response_model=ExamRead, summary="Update an exam")
def update_exam(
    exam_id: uuid.UUID, payload: ExamUpdate, user: CurrentUser, db: DbSession
) -> ExamRead:
    return ExamService(db, user).update(exam_id, payload)


@exams_router.delete("/{exam_id}", response_model=MessageResponse, summary="Delete an exam")
def delete_exam(exam_id: uuid.UUID, user: CurrentUser, db: DbSession) -> MessageResponse:
    ExamService(db, user).delete(exam_id)
    return MessageResponse(message="Exam deleted.")