"""Flashcards, study sessions and recommendations endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, Paging
from app.schemas.common import MessageResponse, Page, PageMeta
from app.schemas.study import (
    FlashcardCreate,
    FlashcardDeckSummary,
    FlashcardRead,
    FlashcardReviewRequest,
    FlashcardReviewResult,
    FlashcardUpdate,
    RecommendationRead,
    RecommendationUpdate,
    StudySessionCreate,
    StudySessionRead,
    WeakTopic,
)
from app.services.insight_service import InsightService
from app.services.study_service import StudyService

flashcards_router = APIRouter(prefix="/flashcards", tags=["flashcards"])
sessions_router = APIRouter(prefix="/sessions", tags=["study sessions"])
recommendations_router = APIRouter(prefix="/recommendations", tags=["insights"])


# ------------------------------------------------------------- flashcards
@flashcards_router.get("", response_model=Page[FlashcardRead], summary="List flashcards")
def list_flashcards(
    user: CurrentUser,
    db: DbSession,
    paging: Paging,
    deck: str | None = None,
    course_id: uuid.UUID | None = None,
    search: str | None = None,
    due_only: bool = Query(default=False, description="Only cards ready for review"),
) -> Page[FlashcardRead]:
    items, total = StudyService(db, user).list_flashcards(
        deck=deck,
        course_id=course_id,
        search=search,
        due_only=due_only,
        limit=paging.limit,
        offset=paging.offset,
    )
    return Page[FlashcardRead](
        items=items,
        meta=PageMeta(
            total=total,
            limit=paging.limit,
            offset=paging.offset,
            has_more=paging.offset + len(items) < total,
        ),
    )


@flashcards_router.post(
    "", response_model=FlashcardRead, status_code=status.HTTP_201_CREATED, summary="Create a flashcard"
)
def create_flashcard(payload: FlashcardCreate, user: CurrentUser, db: DbSession) -> FlashcardRead:
    return StudyService(db, user).create_flashcard(payload)


@flashcards_router.get("/decks", response_model=list[FlashcardDeckSummary], summary="Deck summaries")
def list_decks(user: CurrentUser, db: DbSession) -> list[FlashcardDeckSummary]:
    return StudyService(db, user).decks()


@flashcards_router.get("/due", response_model=list[FlashcardRead], summary="Cards ready to review")
def due_cards(user: CurrentUser, db: DbSession) -> list[FlashcardRead]:
    items, _ = StudyService(db, user).list_flashcards(due_only=True, limit=100)
    return items


@flashcards_router.get("/{card_id}", response_model=FlashcardRead, summary="Get one flashcard")
def get_flashcard(card_id: uuid.UUID, user: CurrentUser, db: DbSession) -> FlashcardRead:
    return StudyService(db, user).get_flashcard(card_id)


@flashcards_router.patch("/{card_id}", response_model=FlashcardRead, summary="Update a flashcard")
def update_flashcard(
    card_id: uuid.UUID, payload: FlashcardUpdate, user: CurrentUser, db: DbSession
) -> FlashcardRead:
    return StudyService(db, user).update_flashcard(card_id, payload)


@flashcards_router.post(
    "/review", response_model=FlashcardReviewResult, summary="Review a card (SM-2 scheduling)"
)
def review_flashcard(
    payload: FlashcardReviewRequest, user: CurrentUser, db: DbSession
) -> FlashcardReviewResult:
    return StudyService(db, user).review_flashcard(payload.card_id, payload.quality)


@flashcards_router.delete("/{card_id}", response_model=MessageResponse, summary="Delete a flashcard")
def delete_flashcard(card_id: uuid.UUID, user: CurrentUser, db: DbSession) -> MessageResponse:
    StudyService(db, user).delete_flashcard(card_id)
    return MessageResponse(message="Flashcard deleted.")


# -------------------------------------------------------- study sessions
@sessions_router.post(
    "",
    response_model=StudySessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Log a study session",
)
def create_session(payload: StudySessionCreate, user: CurrentUser, db: DbSession) -> StudySessionRead:
    return StudyService(db, user).create_session(payload)


@sessions_router.get("", response_model=Page[StudySessionRead], summary="List study sessions")
def list_sessions(user: CurrentUser, db: DbSession, paging: Paging) -> Page[StudySessionRead]:
    items, total = StudyService(db, user).list_sessions(limit=paging.limit, offset=paging.offset)
    return Page[StudySessionRead](
        items=items,
        meta=PageMeta(
            total=total,
            limit=paging.limit,
            offset=paging.offset,
            has_more=paging.offset + len(items) < total,
        ),
    )


@sessions_router.delete(
    "/{session_id}", response_model=MessageResponse, summary="Delete a study session"
)
def delete_session(session_id: uuid.UUID, user: CurrentUser, db: DbSession) -> MessageResponse:
    StudyService(db, user).delete_session(session_id)
    return MessageResponse(message="Study session deleted.")


# --------------------------------------------------------- recommendations
@recommendations_router.get("", response_model=list[RecommendationRead], summary="My recommendations")
def list_recommendations(user: CurrentUser, db: DbSession) -> list[RecommendationRead]:
    return InsightService(db, user).list_recommendations()


@recommendations_router.post(
    "/regenerate",
    response_model=list[RecommendationRead],
    summary="Recompute recommendations from current data",
)
def regenerate(user: CurrentUser, db: DbSession) -> list[RecommendationRead]:
    return InsightService(db, user).regenerate_recommendations()


@recommendations_router.get("/weak-topics", response_model=list[WeakTopic], summary="Weak topics")
async def weak_topics(user: CurrentUser, db: DbSession) -> list[WeakTopic]:
    return await InsightService(db, user).weak_topics()


@recommendations_router.patch(
    "/{recommendation_id}", response_model=RecommendationRead, summary="Mark read / dismissed"
)
def update_recommendation(
    recommendation_id: uuid.UUID,
    payload: RecommendationUpdate,
    user: CurrentUser,
    db: DbSession,
) -> RecommendationRead:
    service = InsightService(db, user)
    return service.mark_recommendation(
        recommendation_id, read=payload.is_read, dismissed=payload.is_dismissed
    )