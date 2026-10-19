"""Tasks, exams and grades."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

TASKS = "/api/v1/tasks"
EXAMS = "/api/v1/exams"
GRADES = "/api/v1/grades"


@pytest.fixture
async def course_id(auth_client: AsyncClient, course_payload: dict) -> str:
    return (await auth_client.post("/api/v1/courses", json=course_payload)).json()["id"]


# ------------------------------------------------------------------- tasks
async def test_create_task_with_course(auth_client: AsyncClient, course_id: str) -> None:
    due = datetime.now(UTC) + timedelta(days=2)
    response = await auth_client.post(
        TASKS,
        json={
            "title": "Practica subnetting",
            "description": "Resolver 10 ejercicios",
            "course_id": course_id,
            "priority": "high",
            "due_at": due.isoformat(),
            "estimated_minutes": 90,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["priority"] == "high"
    assert body["course"]["id"] == course_id
    assert body["is_overdue"] is False


async def test_task_requires_enrolled_course(
    auth_client: AsyncClient, other_user_token: str
) -> None:

    from app.models.user import User  # noqa: F401

    response = await auth_client.post(
        TASKS, json={"title": "Tarea ajena", "course_id": str(uuid.uuid4())}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "course_not_accessible"


async def test_task_crud_cycle(auth_client: AsyncClient, course_id: str) -> None:
    created = (
        await auth_client.post(TASKS, json={"title": "Tarea 1", "course_id": course_id})
    ).json()

    fetched = await auth_client.get(f"{TASKS}/{created['id']}")
    assert fetched.json()["title"] == "Tarea 1"

    updated = await auth_client.patch(
        f"{TASKS}/{created['id']}", json={"title": "Tarea 1 editada", "priority": "urgent"}
    )
    assert updated.json()["title"] == "Tarea 1 editada"
    assert updated.json()["priority"] == "urgent"

    assert (await auth_client.delete(f"{TASKS}/{created['id']}")).status_code == 200
    assert (await auth_client.get(f"{TASKS}/{created['id']}")).status_code == 404


async def test_toggle_completes_and_reopens(auth_client: AsyncClient, course_id: str) -> None:
    created = (await auth_client.post(TASKS, json={"title": "Toggle", "course_id": course_id})).json()

    done = await auth_client.post(f"{TASKS}/{created['id']}/toggle")
    assert done.json()["status"] == "completed"
    assert done.json()["completed_at"] is not None

    reopened = await auth_client.post(f"{TASKS}/{created['id']}/toggle")
    assert reopened.json()["status"] == "pending"
    assert reopened.json()["completed_at"] is None


async def test_overdue_task_is_flagged(auth_client: AsyncClient, course_id: str) -> None:
    past = datetime.now(UTC) - timedelta(days=3)
    created = (
        await auth_client.post(
            TASKS,
            json={"title": "Vencida", "course_id": course_id, "due_at": past.isoformat()},
        )
    ).json()
    assert created["is_overdue"] is True

    completed = await auth_client.post(f"{TASKS}/{created['id']}/toggle")
    assert completed.json()["is_overdue"] is False


async def test_task_filters_and_pagination(auth_client: AsyncClient, course_id: str) -> None:
    await auth_client.post(TASKS, json={"title": "Alpha tarea", "course_id": course_id, "priority": "high"})
    await auth_client.post(TASKS, json={"title": "Beta tarea", "course_id": course_id, "priority": "low"})

    high = await auth_client.get(f"{TASKS}?priority=high")
    assert high.json()["meta"]["total"] == 1
    assert high.json()["items"][0]["title"] == "Alpha tarea"

    searched = await auth_client.get(f"{TASKS}?search=beta")
    assert searched.json()["meta"]["total"] == 1

    paged = await auth_client.get(f"{TASKS}?limit=1&offset=0")
    assert len(paged.json()["items"]) == 1
    assert paged.json()["meta"]["has_more"] is True


async def test_tasks_are_private(
    client: AsyncClient, auth_client: AsyncClient, course_id: str, other_user_token: str
) -> None:
    created = (await auth_client.post(TASKS, json={"title": "Privada", "course_id": course_id})).json()
    intruder = await client.get(
        f"{TASKS}/{created['id']}", headers={"Authorization": f"Bearer {other_user_token}"}
    )
    assert intruder.status_code == 404


# ------------------------------------------------------------------- exams
async def test_create_exam_and_days_until(auth_client: AsyncClient, course_id: str) -> None:
    scheduled = datetime.now(UTC) + timedelta(days=5)
    response = await auth_client.post(
        EXAMS,
        json={
            "title": "Primer parcial",
            "course_id": course_id,
            "exam_type": "partial",
            "scheduled_at": scheduled.isoformat(),
            "duration_minutes": 90,
            "location": "Aula 204",
            "topics": "Subnetting, TCP, UDP",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "scheduled"
    assert body["days_until"] in {4, 5}
    assert body["course"]["id"] == course_id


async def test_upcoming_exams_only(auth_client: AsyncClient, course_id: str) -> None:
    await auth_client.post(
        EXAMS,
        json={
            "title": "Futuro",
            "course_id": course_id,
            "scheduled_at": (datetime.now(UTC) + timedelta(days=10)).isoformat(),
        },
    )
    await auth_client.post(
        EXAMS,
        json={
            "title": "Pasado",
            "course_id": course_id,
            "scheduled_at": (datetime.now(UTC) - timedelta(days=10)).isoformat(),
        },
    )
    upcoming = await auth_client.get(f"{EXAMS}?upcoming_only=true")
    assert upcoming.json()["meta"]["total"] == 1
    assert upcoming.json()["items"][0]["title"] == "Futuro"


# ------------------------------------------------------------------ grades
async def test_create_grade_and_percentage(auth_client: AsyncClient, course_id: str) -> None:
    response = await auth_client.post(
        GRADES,
        json={
            "title": "Practica 1",
            "course_id": course_id,
            "category": "practice",
            "score": 42,
            "max_score": 50,
        },
    )
    assert response.status_code == 201
    assert response.json()["percentage"] == 84.0


async def test_score_cannot_exceed_max(auth_client: AsyncClient, course_id: str) -> None:
    response = await auth_client.post(
        GRADES, json={"title": "Imposible", "course_id": course_id, "score": 120, "max_score": 100}
    )
    assert response.status_code == 422


async def test_grade_overview_aggregates(auth_client: AsyncClient, course_payload: dict) -> None:
    strong = (await auth_client.post("/api/v1/courses", json=course_payload)).json()
    weak = (
        await auth_client.post(
            "/api/v1/courses",
            json={**course_payload, "code": "ALGO-202", "name": "Algoritmos"},
        )
    ).json()

    for score in (90, 70):
        await auth_client.post(
            GRADES, json={"title": f"Nota {score}", "course_id": strong["id"], "score": score}
        )
    await auth_client.post(
        GRADES, json={"title": "Nota baja", "course_id": weak["id"], "score": 40}
    )

    overview = await auth_client.get(f"{GRADES}/overview")
    assert overview.status_code == 200
    body = overview.json()
    assert body["overall_average"] == pytest.approx(66.67, abs=0.1)
    assert body["courses"][0]["course_code"] == "ALGO-202"
    assert body["courses"][0]["average"] == 40.0
    assert body["courses"][0]["required_to_pass"] is not None
    assert sum(bucket["count"] for bucket in body["distribution"]) == 3
    assert body["category_breakdown"]


async def test_grade_updates_exam_status(auth_client: AsyncClient, course_id: str) -> None:
    exam = (
        await auth_client.post(
            EXAMS,
            json={
                "title": "Parcial 2",
                "course_id": course_id,
                "scheduled_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
            },
        )
    ).json()

    await auth_client.post(
        GRADES,
        json={"title": "Parcial 2", "course_id": course_id, "score": 88, "exam_id": exam["id"]},
    )

    refreshed = await auth_client.get(f"{EXAMS}/{exam['id']}")
    assert refreshed.json()["status"] == "completed"