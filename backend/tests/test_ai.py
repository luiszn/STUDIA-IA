"""AI endpoints: chat, summarisation, questions, flashcards, explain, status."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient

AI = "/api/v1/ai"


@pytest.fixture
async def course_id(auth_client: AsyncClient, course_payload: dict) -> str:
    return (await auth_client.post("/api/v1/courses", json=course_payload)).json()["id"]


@pytest.fixture
async def document_id(auth_client: AsyncClient, sample_txt: Path) -> str:
    with sample_txt.open("rb") as handle:
        response = await auth_client.post(
            "/api/v1/documents/upload", files={"file": (sample_txt.name, handle, "text/plain")}
        )
    assert response.status_code == 201, response.text
    return response.json()["id"]


# ------------------------------------------------------------------- status
async def test_ai_status_reports_active_provider(auth_client: AsyncClient) -> None:
    response = await auth_client.get(f"{AI}/status")
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] in {"local", "ollama", "openai"}
    assert body["available"] is True
    assert body["model"]


async def test_ai_status_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get(f"{AI}/status")).status_code == 401


# --------------------------------------------------------------------- chat
async def test_chat_creates_conversation(auth_client: AsyncClient, course_id: str) -> None:
    response = await auth_client.post(
        f"{AI}/chat", json={"message": "Hola, resumen breve de TCP", "course_id": course_id}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["message"]
    assert body["conversation_id"]
    assert body["used_rag"] is False
    assert body["latency_ms"] >= 0
    assert body["title"]


async def test_chat_reuses_conversation(auth_client: AsyncClient) -> None:
    first = (await auth_client.post(f"{AI}/chat", json={"message": "Primera pregunta"})).json()
    second = (
        await auth_client.post(
            f"{AI}/chat",
            json={"message": "Segunda pregunta", "conversation_id": first["conversation_id"]},
        )
    ).json()

    assert second["conversation_id"] == first["conversation_id"]

    detail = await auth_client.get(f"{AI}/conversations/{first['conversation_id']}")
    assert detail.json()["message_count"] == 4


async def test_list_and_rename_conversation(auth_client: AsyncClient) -> None:
    created = (await auth_client.post(f"{AI}/chat", json={"message": "Sin titulo"})).json()

    listing = await auth_client.get(f"{AI}/conversations")
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    renamed = await auth_client.patch(
        f"{AI}/conversations/{created['conversation_id']}", json={"title": "Repaso de redes"}
    )
    assert renamed.json()["title"] == "Repaso de redes"

    deleted = await auth_client.delete(f"{AI}/conversations/{created['conversation_id']}")
    assert deleted.status_code == 200
    assert (await auth_client.get(f"{AI}/conversations")).json() == []


async def test_conversation_is_private(
    client: AsyncClient, auth_client: AsyncClient, other_user_token: str
) -> None:
    created = (await auth_client.post(f"{AI}/chat", json={"message": "Privado"})).json()
    response = await client.get(
        f"{AI}/conversations/{created['conversation_id']}",
        headers={"Authorization": f"Bearer {other_user_token}"},
    )
    assert response.status_code == 404


async def test_chat_rejects_empty_message(auth_client: AsyncClient) -> None:
    assert (await auth_client.post(f"{AI}/chat", json={"message": ""})).status_code == 422


async def test_chat_rejects_unknown_conversation(auth_client: AsyncClient) -> None:
    response = await auth_client.post(
        f"{AI}/chat", json={"message": "Hola", "conversation_id": str(uuid.uuid4())}
    )
    assert response.status_code == 404


# --------------------------------------------------------------- summarize
async def test_summarize_document(auth_client: AsyncClient, document_id: str) -> None:
    response = await auth_client.post(
        f"{AI}/summarize", json={"document_ids": [document_id], "style": "short"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["summary"]) > 30
    assert body["style"] == "short"
    assert body["sources"]
    assert body["provider"]


async def test_summarize_requires_owned_documents(
    client: AsyncClient, auth_client: AsyncClient, other_user_token: str, document_id: str
) -> None:
    response = await client.post(
        f"{AI}/summarize",
        json={"document_ids": [document_id]},
        headers={"Authorization": f"Bearer {other_user_token}"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "document_not_found"


async def test_summarize_requires_at_least_one_document(auth_client: AsyncClient) -> None:
    assert (await auth_client.post(f"{AI}/summarize", json={"document_ids": []})).status_code == 422


# ---------------------------------------------------------------- questions
async def test_generate_questions_from_documents(
    auth_client: AsyncClient, document_id: str, course_id: str
) -> None:
    response = await auth_client.post(
        f"{AI}/questions",
        json={
            "document_ids": [document_id],
            "course_id": course_id,
            "count": 4,
            "question_types": ["multiple_choice", "true_false"],
            "difficulty": "medium",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["count"] == len(body["questions"]) >= 1
    assert body["questions"][0]["prompt"]
    assert body["questions"][0]["explanation"]

    multiple_choice = [
        question for question in body["questions"] if question["type"] == "multiple_choice"
    ]
    assert multiple_choice, "expected at least one multiple choice question"
    for question in multiple_choice:
        assert len(question["options"]) >= 2
        assert question["correct_option_id"] in {option["id"] for option in question["options"]}


async def test_grade_answers(auth_client: AsyncClient, document_id: str) -> None:
    questions = (
        await auth_client.post(
            f"{AI}/questions", json={"document_ids": [document_id], "count": 3}
        )
    ).json()["questions"]

    payload = {
        "questions": [
            {
                "id": question["id"],
                "type": question["type"],
                "prompt": question["prompt"],
                "options": question["options"],
                "correct_answer": question["correct_answer"],
                "correct_option_id": question.get("correct_option_id"),
                "explanation": question["explanation"],
                "difficulty": question["difficulty"],
            }
            for question in questions
        ],
        "answers": [
            {"question_id": question["id"], "answer": question["correct_answer"]}
            for question in questions
        ],
    }
    response = await auth_client.post(f"{AI}/questions/grade", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["score"] == 100.0
    assert body["correct_count"] == body["total"]
    assert all(answer["is_correct"] for answer in body["answers"])


async def test_grade_detects_wrong_answers(auth_client: AsyncClient, document_id: str) -> None:
    questions = (
        await auth_client.post(
            f"{AI}/questions", json={"document_ids": [document_id], "count": 2}
        )
    ).json()["questions"]

    response = await auth_client.post(
        f"{AI}/questions/grade",
        json={
            "questions": questions,
            "answers": [{"question_id": question["id"], "answer": "respuesta incorrecta"} for question in questions],
        },
    )
    assert response.status_code == 200
    assert response.json()["score"] == 0.0


async def test_grade_requires_matching_question_ids(auth_client: AsyncClient, document_id: str) -> None:
    response = await auth_client.post(
        f"{AI}/questions/grade",
        json={"questions": [], "answers": [{"question_id": "q1", "answer": "a"}]},
    )
    assert response.status_code == 422


# --------------------------------------------------------------- flashcards
async def test_generate_flashcards_and_save(
    auth_client: AsyncClient, document_id: str, course_id: str
) -> None:
    response = await auth_client.post(
        f"{AI}/flashcards",
        json={
            "document_ids": [document_id],
            "count": 5,
            "deck": "Redes",
            "course_id": course_id,
            "save": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] == len(body["flashcards"]) >= 1
    assert all(card["deck"] == "Redes" for card in body["flashcards"])
    assert all(card["origin"] == "ai" for card in body["flashcards"])
    assert body["sources"]

    stored = await auth_client.get("/api/v1/flashcards?deck=Redes")
    assert stored.json()["meta"]["total"] == body["created"]


async def test_generate_flashcards_without_saving(
    auth_client: AsyncClient, document_id: str
) -> None:
    body = (
        await auth_client.post(
            f"{AI}/flashcards", json={"document_ids": [document_id], "count": 3, "save": False}
        )
    ).json()
    assert body["created"] == 0
    assert body["flashcards"]


async def test_flashcard_generation_requires_documents(auth_client: AsyncClient) -> None:
    response = await auth_client.post(f"{AI}/flashcards", json={"document_ids": []})
    assert response.status_code == 422


# ------------------------------------------------------------------ explain
async def test_explain_topic(auth_client: AsyncClient, document_id: str, course_id: str) -> None:
    response = await auth_client.post(
        f"{AI}/explain",
        json={
            "topic": "que es el protocolo TCP",
            "course_id": course_id,
            "document_ids": [document_id],
            "level": "beginner",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"]
    assert body["topic"] == "que es el protocolo TCP"
    assert body["level"] == "beginner"
    assert body["used_rag"] is True
    assert body["sources"]


async def test_explain_topic_rejects_short_topic(auth_client: AsyncClient) -> None:
    assert (await auth_client.post(f"{AI}/explain", json={"topic": "x"})).status_code == 422


# --------------------------------------------------------------- study plan
async def test_create_plan_through_ai_router(auth_client: AsyncClient, course_id: str) -> None:
    response = await auth_client.post(
        f"{AI}/study-plans",
        json={
            "course_id": course_id,
            "total_days": 4,
            "daily_minutes": 60,
            "level": "beginner",
            "use_weak_topics": False,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["days"]) == 4
    assert body["status"] == "draft"
    assert all(day["date"] for day in body["days"])

    listing = await auth_client.get(f"{AI}/study-plans")
    assert len(listing.json()) == 1


async def test_plan_requires_enrolled_course(
    auth_client: AsyncClient, other_user_token: str, client: AsyncClient
) -> None:
    response = await client.post(
        f"{AI}/study-plans",
        json={"course_id": str(uuid.uuid4()), "use_weak_topics": False},
        headers={"Authorization": f"Bearer {other_user_token}"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "course_not_accessible"


async def test_weak_topics_endpoint(auth_client: AsyncClient) -> None:
    response = await auth_client.get(f"{AI}/weak-topics")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ----------------------------------------------------------- provider layer
async def test_provider_falls_back_gracefully() -> None:
    from app.ai.registry import resolve_provider

    resolved = await resolve_provider()
    assert resolved.provider.name in {"local", "ollama", "openai"}
    health = await resolved.provider.health()
    assert health.available is True
    assert health.message


async def test_json_parsing_survives_dirty_output() -> None:
    from app.ai.rag.parsing import extract_json

    assert extract_json('aqui va: {"days": []} fin') == {"days": []}
    assert extract_json("```json\n{\"a\": 1}\n```") == {"a": 1}
    with pytest.raises(ValueError):
        extract_json("no json here")
