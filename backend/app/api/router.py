"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import academic, ai, auth, courses, documents, grades, insights, study

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(courses.router)
api_router.include_router(academic.tasks_router)
api_router.include_router(academic.exams_router)
api_router.include_router(grades.router)
api_router.include_router(documents.router)
api_router.include_router(study.flashcards_router)
api_router.include_router(study.sessions_router)
api_router.include_router(study.recommendations_router)
api_router.include_router(ai.router)
api_router.include_router(insights.router)

__all__ = ["api_router"]