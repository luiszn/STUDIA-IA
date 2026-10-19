"""Dashboard aggregation, calendar range and global search."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.fixture
async def seeded(auth_client: AsyncClient, course_payload: dict) -> dict:
    """A realistic slice of academic data for the dashboard to aggregate."""
    course = (await auth_client.post("/api/v1/courses", json=course_payload)).json()

    await auth_client.post(
        "/api/v1/tasks",
        json={
            "title": "Taller 1",
            "course_id": course["id"],
            "priority": "high",
            "due_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "estimated_minutes": 60,
        },
    )
    completed = await auth_client.post(
        "/api/v1/tasks",
        json={"title": "Laboratorio", "course_id": course["id"], "priority": "low"},
    )
    await auth_client.post(f"/api/v1/tasks/{completed.json()['id']}/toggle")

    await auth_client.post(
        "/api/v1/exams",
        json={
            "title": "Parcial 1",
            "course_id": course["id"],
            "exam_type": "partial",
            "scheduled_at": (datetime.now(UTC) + timedelta(days=4)).isoformat(),
            "location": "Aula 101",
        },
    )
    await auth_client.post(
        "/api/v1/grades",
        json={"title": "Quiz", "course_id": course["id"], "score": 76, "max_score": 100},
    )
    await auth_client.post(
        "/api/v1/sessions",
        json={"focus": "Subnetting", "course_id": course["id"], "duration_minutes": 75},
    )
    await auth_client.post(
        "/api/v1/flashcards",
        json={"front": "TCP", "back": "Fiable", "deck": "Redes", "course_id": course["id"]},
    )
    return course


async def test_dashboard_aggregates_everything(auth_client: AsyncClient, seeded: dict) -> None:
    response = await auth_client.get("/api/v1/dashboard")
    assert response.status_code == 200
    body = response.json()

    stats = body["stats"]
    assert stats["active_courses"] == 1
    assert stats["pending_tasks"] == 1
    assert stats["completed_tasks"] == 1
    assert stats["upcoming_exams"] == 1
    assert stats["next_exam_in_days"] == 4
    assert stats["average_grade"] == 76.0
    assert stats["study_minutes_week"] == 75
    assert stats["flashcards"] == 1
    assert stats["flashcards_due"] == 1
    assert stats["daily_goal_minutes"] > 0

    assert body["greeting"]
    assert body["upcoming"], "dashboard must surface upcoming activity"
    kinds = {item["kind"] for item in body["upcoming"]}
    assert "exam" in kinds and "task" in kinds
    assert body["upcoming"] == sorted(body["upcoming"], key=lambda item: item["date"])

    assert len(body["performance"]["study_minutes"]) == 7
    assert body["performance"]["by_course"][0]["code"] == "REDES-101"
    assert body["quick_actions"]


async def test_dashboard_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/dashboard")).status_code == 401


async def test_calendar_merges_all_sources(auth_client: AsyncClient, seeded: dict) -> None:
    start = date.today() - timedelta(days=1)
    end = date.today() + timedelta(days=30)
    response = await auth_client.get(f"/api/v1/calendar?start={start.isoformat()}&end={end.isoformat()}")

    assert response.status_code == 200
    body = response.json()
    assert body["start"] == start.isoformat()
    assert body["end"] == end.isoformat()

    kinds = {event["kind"] for event in body["events"]}
    assert {"task", "exam", "session"} <= kinds
    for event in body["events"]:
        assert event["path"]
        assert start <= date.fromisoformat(event["date"]) <= end

    assert body["events"] == sorted(body["events"], key=lambda item: item["date"])


async def test_calendar_defaults_to_a_two_month_window(auth_client: AsyncClient) -> None:
    body = (await auth_client.get("/api/v1/calendar")).json()
    start = date.fromisoformat(body["start"])
    end = date.fromisoformat(body["end"])
    assert start.day == 1
    assert end > start


async def test_calendar_excludes_out_of_range(auth_client: AsyncClient, seeded: dict) -> None:
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    body = (await auth_client.get(f"/api/v1/calendar?start={yesterday}&end={yesterday}")).json()
    assert body["events"] == []


async def test_global_search_across_entities(auth_client: AsyncClient, seeded: dict) -> None:
    response = await auth_client.get("/api/v1/search?q=redes")
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "redes"
    assert body["total"] >= 1
    assert body["groups"]
    types = {item["type"] for item in body["results"]}
    assert "course" in types
    for item in body["results"]:
        assert item["path"]


async def test_search_finds_documents_and_flashcards(
    auth_client: AsyncClient, sample_txt, seeded: dict
) -> None:
    with sample_txt.open("rb") as handle:
        await auth_client.post(
            "/api/v1/documents/upload", files={"file": (sample_txt.name, handle, "text/plain")}
        )

    body = (await auth_client.get("/api/v1/search?q=subnetting")).json()
    types = {item["type"] for item in body["results"]}
    assert "document" in types


async def test_search_requires_two_characters(auth_client: AsyncClient) -> None:
    assert (await auth_client.get("/api/v1/search?q=a")).status_code == 422


async def test_search_never_leaks_other_users(
    client: AsyncClient, auth_client: AsyncClient, seeded: dict, other_user_token: str
) -> None:
    response = await client.get(
        "/api/v1/search?q=redes", headers={"Authorization": f"Bearer {other_user_token}"}
    )
    assert response.json()["total"] == 0


async def test_dashboard_focus_course_suggests_weakest(auth_client: AsyncClient, seeded: dict) -> None:
    second = (
        await auth_client.post(
            "/api/v1/courses",
            json={"code": "ALGO-202", "name": "Algoritmos II", "credits": 3},
        )
    ).json()
    await auth_client.post(
        "/api/v1/grades", json={"title": "Nota", "course_id": second["id"], "score": 41}
    )

    body = (await auth_client.get("/api/v1/dashboard")).json()
    assert body["focus_course"] is not None
    assert body["focus_course"]["average"] == 41.0
