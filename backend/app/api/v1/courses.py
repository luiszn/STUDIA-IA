"""Course endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.models.enums import CourseStatus
from app.schemas.common import MessageResponse
from app.schemas.course import CourseCreate, CourseRead, CourseStats, CourseUpdate
from app.services.course_service import CourseService

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseRead], summary="List my courses")
def list_courses(
    user: CurrentUser,
    db: DbSession,
    course_status: CourseStatus | None = Query(default=None, alias="status"),
) -> list[CourseRead]:
    return CourseService(db, user).list(course_status)


@router.post(
    "", response_model=CourseRead, status_code=status.HTTP_201_CREATED, summary="Create a course"
)
def create_course(payload: CourseCreate, user: CurrentUser, db: DbSession) -> CourseRead:
    return CourseService(db, user).create(payload)


@router.get("/{course_id}", response_model=CourseRead, summary="Get one course")
def get_course(course_id: uuid.UUID, user: CurrentUser, db: DbSession) -> CourseRead:
    return CourseService(db, user).get(course_id)


@router.put("/{course_id}", response_model=CourseRead, summary="Replace a course")
def replace_course(
    course_id: uuid.UUID, payload: CourseCreate, user: CurrentUser, db: DbSession
) -> CourseRead:
    service = CourseService(db, user)
    service.update(course_id, CourseUpdate(**payload.model_dump()))
    return service.get(course_id)


@router.patch("/{course_id}", response_model=CourseRead, summary="Update a course")
def update_course(
    course_id: uuid.UUID, payload: CourseUpdate, user: CurrentUser, db: DbSession
) -> CourseRead:
    return CourseService(db, user).update(course_id, payload)


@router.delete("/{course_id}", response_model=MessageResponse, summary="Delete a course")
def delete_course(course_id: uuid.UUID, user: CurrentUser, db: DbSession) -> MessageResponse:
    CourseService(db, user).delete(course_id)
    return MessageResponse(message="Course deleted.")


@router.get("/{course_id}/stats", response_model=CourseStats, summary="Course statistics")
def course_stats(course_id: uuid.UUID, user: CurrentUser, db: DbSession) -> CourseStats:
    return CourseService(db, user).stats(course_id)