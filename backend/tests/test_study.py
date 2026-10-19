"""Flashcards (SM-2), study sessions, study plans and recommendations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

CARDS = "/api/v1/flashcards"
SESSIONS = "/api/v1/sessions"
PLANS = "/api/v1/ai/study-plans"
RECOMMENDATIONS = "/api/v1/recommendations"


@pytest.fixture
async def course_id(auth_client: AsyncClient, course_payload: dict) -> str:
    return (await auth_client.post("/api/v1/courses", json=course_payload)).json()["id"]


# --------------------------------------------------------------- flashcards
async def test_create_flashcard(auth_client: AsyncClient, course_id: str) -> None:
    response = await auth_client.post(
        CARDS,
        json={
            "front": "¿Que es el subnetting?",
            "back": "Division de una red IP en subredes mas pequenas.",
            "deck": "Redes",
            "course_id": course_id,
            "tags": ["subnetting", "ipv4"],
            "difficulty": "hard",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "new"
    assert body["origin"] == "manual"
    assert body["tags"] == ["subnetting", "ipv4"]
    assert body["ease_factor"] == 2.5
    assert body["course"]["id"] == course_id


async def test_create_bulk_flashcards(auth_client: AsyncClient) -> None:
    response = await auth_client.post(
        CARDS,
        json={"front": "Pregunta", "back": "Respuesta", "deck": "Lote", "tags": ["x"]},
    )
    assert response.status_code == 201, response.text
    assert response.json()["tags"] == ["x"]


async def test_list_and_filter_flashcards(auth_client: AsyncClient, course_id: str) -> None:
    await auth_client.post(CARDS, json={"front": "TCP", "back": "Orientado a conexion", "deck": "Protocolos"})
    await auth_client.post(CARDS, json={"front": "UDP", "back": "Sin conexion", "deck": "Protocolos"})
    await auth_client.post(CARDS, json={"front": "ARP", "back": "IP a MAC", "deck": "Capa 2"})

    by_deck = await auth_client.get(f"{CARDS}?deck=Protocolos")
    assert by_deck.json()["meta"]["total"] == 2

    searched = await auth_client.get(f"{CARDS}?search=ARP")
    assert searched.json()["meta"]["total"] == 1


async def test_due_cards_exclude_scheduled_ones(auth_client: AsyncClient) -> None:
    due = (await auth_client.post(CARDS, json={"front": "Debe salir", "back": "Ya"})).json()
    future = (
        await auth_client.post(CARDS, json={"front": "Programada", "back": "Todavia no"})
    ).json()

    from datetime import UTC as _UTC

    from app.db.session import get_db
    from app.main import app as fastapi_app
    from app.models.study import Flashcard

    override = fastapi_app.dependency_overrides[get_db]
    session = next(override())
    card = session.get(Flashcard, uuid.UUID(str(future["id"])))
    card.next_review_at = datetime.now(_UTC) + timedelta(days=5)
    session.commit()

    due_ids = [card["id"] for card in (await auth_client.get(f"{CARDS}/due")).json()]
    assert due["id"] in due_ids
    assert future["id"] not in due_ids


async def test_review_lapses_on_bad_quality(auth_client: AsyncClient) -> None:
    card = (await auth_client.post(CARDS, json={"front": "Repaso", "back": "Espaciado"})).json()

    reviewed = await auth_client.post(
        f"{CARDS}/review", json={"card_id": card["id"], "quality": 1, "response_seconds": 40}
    )
    assert reviewed.status_code == 200, reviewed.text
    body = reviewed.json()
    assert body["status"] == "learning"
    assert body["repetitions"] == 0
    assert body["interval_days"] >= 0


async def test_review_gradually_masters_card(auth_client: AsyncClient) -> None:
    card = (await auth_client.post(CARDS, json={"front": "Repaso largo", "back": "SM-2"})).json()
    intervals = []
    for _ in range(4):
        response = await auth_client.post(f"{CARDS}/review", json={"card_id": card["id"], "quality": 5})
        assert response.status_code == 200
        intervals.append(response.json()["interval_days"])

    assert intervals[0] == 1
    assert intervals == sorted(intervals)
    final = await auth_client.get(f"{CARDS}/{card['id']}")
    assert final.json()["status"] in {"review", "mastered"}


async def test_review_rejects_invalid_quality(auth_client: AsyncClient) -> None:
    card = (await auth_client.post(CARDS, json={"front": "X", "back": "Y"})).json()
    response = await auth_client.post(f"{CARDS}/review", json={"card_id": card["id"], "quality": 9})
    assert response.status_code == 422


async def test_decks_aggregate_cards(auth_client: AsyncClient) -> None:
    await auth_client.post(CARDS, json={"front": "A", "back": "1", "deck": "Redes", "difficulty": "easy"})
    await auth_client.post(CARDS, json={"front": "B", "back": "2", "deck": "Redes", "difficulty": "hard"})
    await auth_client.post(CARDS, json={"front": "C", "back": "3", "deck": "Protocolos"})

    decks = (await auth_client.get(f"{CARDS}/decks")).json()
    by_name = {deck["name"]: deck for deck in decks}
    assert by_name["Redes"]["total"] == 2
    assert by_name["Redes"]["new"] == 2
    assert by_name["Redes"]["average_difficulty"] == 2.0


async def test_update_and_delete_flashcard(auth_client: AsyncClient) -> None:
    card = (await auth_client.post(CARDS, json={"front": "Vieja", "back": "Card"})).json()

    updated = await auth_client.patch(f"{CARDS}/{card['id']}", json={"front": "Nueva", "status": "review"})
    assert updated.json()["front"] == "Nueva"

    assert (await auth_client.delete(f"{CARDS}/{card['id']}")).status_code == 200
    assert (await auth_client.get(f"{CARDS}/{card['id']}")).status_code == 404


async def test_flashcards_are_private(
    client: AsyncClient, auth_client: AsyncClient, other_user_token: str
) -> None:
    card = (await auth_client.post(CARDS, json={"front": "Secreta", "back": "Card"})).json()
    response = await client.get(
        f"{CARDS}/{card['id']}", headers={"Authorization": f"Bearer {other_user_token}"}
    )
    assert response.status_code == 404


# ----------------------------------------------------------------- sessions
async def test_log_study_session(auth_client: AsyncClient, course_id: str) -> None:
    started = datetime.now(UTC) - timedelta(minutes=90)
    response = await auth_client.post(
        SESSIONS,
        json={
            "focus": "Subnetting",
            "course_id": course_id,
            "started_at": started.isoformat(),
            "duration_minutes": 90,
            "notes": "Resueltos 8 ejercicios",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["duration_minutes"] == 90
    assert body["course"]["id"] == course_id
    assert body["ended_at"] is not None


async def test_list_sessions_and_streak(auth_client: AsyncClient) -> None:
    await auth_client.post(SESSIONS, json={"focus": "Repaso 1", "duration_minutes": 60})
    await auth_client.post(SESSIONS, json={"focus": "Repaso 2", "duration_minutes": 30})

    response = await auth_client.get(f"{SESSIONS}?limit=10")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 2
    assert len(body["items"]) == 2
    assert all(item["course"] is None for item in body["items"])

    dashboard = (await auth_client.get("/api/v1/dashboard")).json()
    assert dashboard["stats"]["study_minutes_total"] == 90
    assert dashboard["stats"]["study_streak_days"] >= 1


async def test_delete_session(auth_client: AsyncClient) -> None:
    session = (await auth_client.post(SESSIONS, json={"focus": "Temporal", "duration_minutes": 10})).json()
    assert (await auth_client.delete(f"{SESSIONS}/{session['id']}")).status_code == 200


# --------------------------------------------------------------- study plans
async def test_generate_study_plan(auth_client: AsyncClient, course_id: str) -> None:
    response = await auth_client.post(
        PLANS,
        json={
            "course_id": course_id,
            "total_days": 5,
            "daily_minutes": 90,
            "level": "intermediate",
            "focus_topics": ["subnetting", "TCP"],
            "use_weak_topics": False,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["total_days"] == 5
    assert body["daily_minutes"] == 90
    assert len(body["days"]) == 5
    assert body["total_minutes"] > 0
    assert body["days"][0]["date"] is not None
    assert body["course"]["id"] == course_id
    assert body["rationale"]


async def test_convert_study_plan_into_tasks_and_sessions(
    auth_client: AsyncClient, course_id: str
) -> None:
    plan = (
        await auth_client.post(
            PLANS,
            json={
                "course_id": course_id,
                "total_days": 3,
                "daily_minutes": 60,
                "use_weak_topics": False,
            },
        )
    ).json()

    response = await auth_client.post(
        f"{PLANS}/{plan['id']}/convert", json={"create_tasks": True, "create_sessions": True}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tasks_created"] == 3
    assert body["sessions_created"] == 3
    assert body["plan"]["status"] == "active"

    tasks = await auth_client.get("/api/v1/tasks")
    assert tasks.json()["meta"]["total"] == 3


async def test_delete_study_plan(auth_client: AsyncClient) -> None:
    plan = (
        await auth_client.post(
            PLANS, json={"total_days": 2, "daily_minutes": 30, "use_weak_topics": False}
        )
    ).json()
    assert (await auth_client.delete(f"{PLANS}/{plan['id']}")).status_code == 200
    assert (await auth_client.get(f"{PLANS}/{plan['id']}")).status_code == 404


# ----------------------------------------------------------- recommendations
async def test_recommendations_and_weak_topics(auth_client: AsyncClient, course_id: str) -> None:
    await auth_client.post(
        "/api/v1/tasks",
        json={"title": "Tarea vencida", "course_id": course_id, "due_at": "2020-01-01T00:00:00Z"},
    )
    await auth_client.post(
        "/api/v1/grades", json={"title": "Nota mala", "course_id": course_id, "score": 35}
    )

    response = await auth_client.get(RECOMMENDATIONS)
    assert response.status_code == 200
    items = response.json()
    assert items, "expected at least one recommendation"
    kinds = {item["kind"] for item in items}
    assert "priority_task" in kinds or "weak_topic" in kinds

    weak = await auth_client.get(f"{RECOMMENDATIONS}/weak-topics")
    assert weak.status_code == 200
    assert isinstance(weak.json(), list)


async def test_mark_recommendation_as_read(auth_client: AsyncClient, course_id: str) -> None:
    await auth_client.post(
        "/api/v1/tasks",
        json={"title": "Vencida", "course_id": course_id, "due_at": "2020-01-01T00:00:00Z"},
    )
    items = (await auth_client.get(RECOMMENDATIONS)).json()
    target = items[0]["id"]

    updated = await auth_client.patch(f"{RECOMMENDATIONS}/{target}", json={"is_read": True})
    assert updated.status_code == 200
    assert updated.json()["is_read"] is True


async def test_regenerate_recommendations(auth_client: AsyncClient, course_id: str) -> None:
    await auth_client.post(
        "/api/v1/tasks",
        json={"title": "Vencida", "course_id": course_id, "due_at": "2020-01-01T00:00:00Z"},
    )
    response = await auth_client.post(f"{RECOMMENDATIONS}/regenerate")
    assert response.status_code == 200
    assert response.json()


async def test_empty_dashboard_has_safe_defaults(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/v1/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["stats"]["active_courses"] == 0
    assert body["stats"]["pending_tasks"] == 0
    assert body["upcoming"] == []
    assert body["performance"]["study_minutes"]
    assert body["recommendation"] is None
    assert body["quick_actions"]