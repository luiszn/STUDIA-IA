"""Course management and ownership isolation."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

ENDPOINT = "/api/v1/courses"


async def test_create_and_list_course(auth_client: AsyncClient, course_payload: dict) -> None:
    created = await auth_client.post(ENDPOINT, json=course_payload)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["code"] == "REDES-101"
    assert body["role"] == "owner"
    assert body["pending_task_count"] == 0

    listing = await auth_client.get(ENDPOINT)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["id"] == body["id"]


async def test_code_is_normalised_to_uppercase(auth_client: AsyncClient, course_payload: dict) -> None:
    created = await auth_client.post(ENDPOINT, json={**course_payload, "code": "redes-101"})
    assert created.json()["code"] == "REDES-101"


async def test_duplicate_code_is_rejected(auth_client: AsyncClient, course_payload: dict) -> None:
    await auth_client.post(ENDPOINT, json=course_payload)
    duplicate = await auth_client.post(ENDPOINT, json={**course_payload, "name": "Otra materia"})
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_course"


async def test_invalid_color_is_rejected(auth_client: AsyncClient, course_payload: dict) -> None:
    response = await auth_client.post(ENDPOINT, json={**course_payload, "color": "orange"})
    assert response.status_code == 422


async def test_patch_course(auth_client: AsyncClient, course_payload: dict) -> None:
    created = (await auth_client.post(ENDPOINT, json=course_payload)).json()
    updated = await auth_client.patch(
        f"{ENDPOINT}/{created['id']}", json={"professor": "Dr. nesting", "credits": 5}
    )
    assert updated.status_code == 200
    assert updated.json()["credits"] == 5


async def test_put_course_replaces_fields(auth_client: AsyncClient, course_payload: dict) -> None:
    created = (await auth_client.post(ENDPOINT, json=course_payload)).json()
    response = await auth_client.put(
        f"{ENDPOINT}/{created['id']}", json={**course_payload, "name": "Redes II"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Redes II"


async def test_course_stats(auth_client: AsyncClient, course_payload: dict) -> None:
    created = (await auth_client.post(ENDPOINT, json=course_payload)).json()
    await auth_client.post(
        "/api/v1/tasks", json={"title": "Ejercicio 1", "course_id": created["id"], "priority": "high"}
    )
    await auth_client.post(
        "/api/v1/grades",
        json={"title": "Parcial 1", "course_id": created["id"], "score": 82, "max_score": 100},
    )

    stats = await auth_client.get(f"{ENDPOINT}/{created['id']}/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["total_tasks"] == 1
    assert body["completed_tasks"] == 0
    assert body["average_grade"] == 82.0
    assert body["documents"] == 0


async def test_unknown_course_returns_structured_404(auth_client: AsyncClient) -> None:
    response = await auth_client.get(f"{ENDPOINT}/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "course_not_found"


async def test_courses_are_private_per_user(
    client: AsyncClient, auth_client: AsyncClient, course_payload: dict, other_user_token: str
) -> None:
    created = (await auth_client.post(ENDPOINT, json=course_payload)).json()

    intruder = await client.get(
        f"{ENDPOINT}/{created['id']}", headers={"Authorization": f"Bearer {other_user_token}"}
    )
    assert intruder.status_code == 404

    listing = await client.get(ENDPOINT, headers={"Authorization": f"Bearer {other_user_token}"})
    assert listing.json() == []


async def test_delete_course(auth_client: AsyncClient, course_payload: dict) -> None:
    created = (await auth_client.post(ENDPOINT, json=course_payload)).json()
    deleted = await auth_client.delete(f"{ENDPOINT}/{created['id']}")
    assert deleted.status_code == 200
    assert (await auth_client.get(f"{ENDPOINT}/{created['id']}")).status_code == 404


async def test_filter_by_status(auth_client: AsyncClient, course_payload: dict) -> None:
    created = (await auth_client.post(ENDPOINT, json=course_payload)).json()
    await auth_client.patch(f"{ENDPOINT}/{created['id']}", json={"status": "completed"})

    active = await auth_client.get(f"{ENDPOINT}?status=active")
    assert active.json() == []

    completed = await auth_client.get(f"{ENDPOINT}?status=completed")
    assert len(completed.json()) == 1


@pytest.mark.parametrize("code,name", [("R", "x"), ("REDES-101", "y")])
async def test_minimum_field_length(
    auth_client: AsyncClient, course_payload: dict, code: str, name: str
) -> None:
    response = await auth_client.post(ENDPOINT, json={**course_payload, "code": code, "name": name})
    assert response.status_code == 422