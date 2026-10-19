"""Authentication: registration, login, tokens, profile, isolation."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

REGISTRATION = {
    "email": "nuevo@studia.ai",
    "password": "Secret1234",
    "full_name": "Laura Gómez",
    "university": "Universidad de Antioquia",
    "career": "Ingeniería de Sistemas",
}

ENDPOINT = "/api/v1/auth"


async def test_register_returns_tokens_and_user(client: AsyncClient) -> None:
    response = await client.post(f"{ENDPOINT}/register", json=REGISTRATION)
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "nuevo@studia.ai"
    assert body["user"]["initials"] == "LG"
    assert "hashed_password" not in body["user"]


async def test_register_rejects_duplicate_email(client: AsyncClient) -> None:
    await client.post(f"{ENDPOINT}/register", json=REGISTRATION)
    response = await client.post(f"{ENDPOINT}/register", json=REGISTRATION)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


async def test_register_rejects_weak_password(client: AsyncClient) -> None:
    response = await client.post(
        f"{ENDPOINT}/register", json={**REGISTRATION, "password": "abc"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_register_rejects_password_without_digits(client: AsyncClient) -> None:
    response = await client.post(
        f"{ENDPOINT}/register", json={**REGISTRATION, "password": "onlyletters"}
    )
    assert response.status_code == 422
    assert "fields" in response.json()["error"]["details"]


async def test_login_and_me(client: AsyncClient) -> None:
    await client.post(f"{ENDPOINT}/register", json=REGISTRATION)
    response = await client.post(
        f"{ENDPOINT}/login", json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = await client.get(f"{ENDPOINT}/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["full_name"] == "Laura Gómez"


async def test_login_with_wrong_password(client: AsyncClient) -> None:
    await client.post(f"{ENDPOINT}/register", json=REGISTRATION)
    response = await client.post(
        f"{ENDPOINT}/login", json={"email": REGISTRATION["email"], "password": "WrongPass99"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_login_unknown_email_is_generic(client: AsyncClient) -> None:
    response = await client.post(
        f"{ENDPOINT}/login", json={"email": "ghost@studia.ai", "password": "Secret1234"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_protected_route_requires_token(client: AsyncClient) -> None:
    response = await client.get(f"{ENDPOINT}/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "missing_credentials"


async def test_invalid_token_is_rejected(client: AsyncClient) -> None:
    response = await client.get(f"{ENDPOINT}/me", headers={"Authorization": "Bearer nonsense"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_token"


async def test_refresh_token_flow(client: AsyncClient) -> None:
    created = await client.post(f"{ENDPOINT}/register", json=REGISTRATION)
    refresh = created.json()["refresh_token"]
    response = await client.post(f"{ENDPOINT}/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_access_token_cannot_be_used_as_refresh(client: AsyncClient) -> None:
    created = await client.post(f"{ENDPOINT}/register", json=REGISTRATION)
    response = await client.post(
        f"{ENDPOINT}/refresh", json={"refresh_token": created.json()["access_token"]}
    )
    assert response.status_code == 401


async def test_update_profile(auth_client: AsyncClient) -> None:
    response = await auth_client.patch(
        f"{ENDPOINT}/me", json={"career": "MAESTRIA EN SISTEMAS", "daily_study_goal_minutes": 180}
    )
    assert response.status_code == 200
    assert response.json()["career"] == "MAESTRIA EN SISTEMAS"
    assert response.json()["daily_study_goal_minutes"] == 180


async def test_change_password_requires_current(auth_client: AsyncClient) -> None:
    bad = await auth_client.post(
        f"{ENDPOINT}/me/password", json={"current_password": "Nope1234", "new_password": "NewPass123"}
    )
    assert bad.status_code == 401

    good = await auth_client.post(
        f"{ENDPOINT}/me/password",
        json={"current_password": "Secret1234", "new_password": "NewPass123"},
    )
    assert good.status_code == 200


async def test_password_reset_flow(client: AsyncClient) -> None:
    await client.post(f"{ENDPOINT}/register", json=REGISTRATION)

    request = await client.post(f"{ENDPOINT}/password-reset", json={"email": REGISTRATION["email"]})
    assert request.status_code == 200
    assert "If that email exists" in request.json()["message"]

    # The endpoint must not leak whether the account exists.
    ghost = await client.post(f"{ENDPOINT}/password-reset", json={"email": "ghost@studia.ai"})
    assert ghost.json()["message"] == request.json()["message"]


async def test_health_is_public(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "degraded"}


async def test_unknown_route_returns_structured_error(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("field", ["email", "password", "full_name"])
async def test_registration_requires_core_fields(client: AsyncClient, field: str) -> None:
    payload = {key: value for key, value in REGISTRATION.items() if key != field}
    response = await client.post(f"{ENDPOINT}/register", json=payload)
    assert response.status_code == 422