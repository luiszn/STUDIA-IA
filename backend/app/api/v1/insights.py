"""Dashboard, calendar and global search endpoints."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.dashboard import CalendarResponse, DashboardResponse, SearchResponse
from app.services.insight_service import InsightService

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardResponse, summary="Aggregated dashboard")
def dashboard(user: CurrentUser, db: DbSession) -> DashboardResponse:
    return InsightService(db, user).dashboard()


@router.get("/calendar", response_model=CalendarResponse, summary="Academic calendar range")
def calendar(
    user: CurrentUser,
    db: DbSession,
    start: date | None = Query(default=None, description="Defaults to the start of this month"),
    end: date | None = Query(default=None, description="Defaults to the end of next month"),
) -> CalendarResponse:
    today = date.today()
    start_date = start or today.replace(day=1)
    end_date = end or (start_date + timedelta(days=60))
    return InsightService(db, user).calendar(start_date, end_date)


@router.get("/search", response_model=SearchResponse, summary="Global search (Ctrl+K)")
def search(
    user: CurrentUser,
    db: DbSession,
    q: str = Query(min_length=2, description="At least two characters"),
    limit: int = Query(default=6, ge=1, le=20),
) -> SearchResponse:
    return InsightService(db, user).search(q, limit=limit)