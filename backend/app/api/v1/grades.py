"""Grade endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession, Paging
from app.schemas.academic import GradeCreate, GradeOverview, GradeRead, GradeUpdate
from app.schemas.common import MessageResponse, Page, PageMeta
from app.services.academic_service import GradeService

router = APIRouter(prefix="/grades", tags=["grades"])


@router.get("", response_model=Page[GradeRead], summary="List grades")
def list_grades(
    user: CurrentUser,
    db: DbSession,
    paging: Paging,
    course_id: uuid.UUID | None = None,
) -> Page[GradeRead]:
    items, total = GradeService(db, user).list(
        course_id=course_id, limit=paging.limit, offset=paging.offset
    )
    return Page[GradeRead](
        items=items,
        meta=PageMeta(
            total=total,
            limit=paging.limit,
            offset=paging.offset,
            has_more=paging.offset + len(items) < total,
        ),
    )


@router.post(
    "", response_model=GradeRead, status_code=status.HTTP_201_CREATED, summary="Register a grade"
)
def create_grade(payload: GradeCreate, user: CurrentUser, db: DbSession) -> GradeRead:
    return GradeService(db, user).create(payload)


@router.get("/overview", response_model=GradeOverview, summary="Performance overview")
def overview(user: CurrentUser, db: DbSession) -> GradeOverview:
    return GradeService(db, user).overview()


@router.get("/{grade_id}", response_model=GradeRead, summary="Get one grade")
def get_grade(grade_id: uuid.UUID, user: CurrentUser, db: DbSession) -> GradeRead:
    return GradeService(db, user).get(grade_id)


@router.patch("/{grade_id}", response_model=GradeRead, summary="Update a grade")
def update_grade(
    grade_id: uuid.UUID, payload: GradeUpdate, user: CurrentUser, db: DbSession
) -> GradeRead:
    return GradeService(db, user).update(grade_id, payload)


@router.delete("/{grade_id}", response_model=MessageResponse, summary="Delete a grade")
def delete_grade(grade_id: uuid.UUID, user: CurrentUser, db: DbSession) -> MessageResponse:
    GradeService(db, user).delete(grade_id)
    return MessageResponse(message="Grade deleted.")