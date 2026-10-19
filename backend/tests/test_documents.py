"""Document ingestion, chunking and retrieval (RAG)."""

from __future__ import annotations

import uuid
from pathlib import Path

from httpx import AsyncClient

DOCUMENTS = "/api/v1/documents"


async def upload(
    auth_client: AsyncClient, sample_txt: Path, *, course_id: str | None = None, title: str | None = None
) -> dict:
    data: dict[str, str] = {}
    if course_id:
        data["course_id"] = course_id
    if title:
        data["title"] = title
    with sample_txt.open("rb") as handle:
        response = await auth_client.post(
            f"{DOCUMENTS}/upload",
            files={"file": (sample_txt.name, handle, "text/plain")},
            data=data,
        )
    assert response.status_code == 201, response.text
    return response.json()


async def test_upload_indexes_document(auth_client: AsyncClient, sample_txt: Path) -> None:
    document = await upload(auth_client, sample_txt)

    assert document["status"] == "ready"
    assert document["extension"] == ".txt"
    assert document["word_count"] > 50
    assert document["chunk_count"] >= 1
    assert document["size_bytes"] > 0
    assert document["error_message"] is None


async def test_document_detail_exposes_chunks(auth_client: AsyncClient, sample_txt: Path) -> None:
    document = await upload(auth_client, sample_txt, title="Clase 03")

    detail = await auth_client.get(f"{DOCUMENTS}/{document['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["title"] == "Clase 03"
    assert len(body["chunks"]) == document["chunk_count"]
    assert all(chunk["token_estimate"] > 0 for chunk in body["chunks"])
    assert [chunk["chunk_index"] for chunk in body["chunks"]] == sorted(
        chunk["chunk_index"] for chunk in body["chunks"]
    )
    assert body["preview"]


async def test_upload_attaches_to_course(
    auth_client: AsyncClient, sample_txt: Path, course_payload: dict
) -> None:
    course = (await auth_client.post("/api/v1/courses", json=course_payload)).json()
    document = await upload(auth_client, sample_txt, course_id=course["id"])

    assert document["course"]["id"] == course["id"]

    listing = await auth_client.get(f"{DOCUMENTS}?course_id={course['id']}")
    assert [item["id"] for item in listing.json()] == [document["id"]]


async def test_rejects_unsupported_extension(auth_client: AsyncClient, tmp_path: Path) -> None:
    bad = tmp_path / "malware.exe"
    bad.write_bytes(b"MZ\x90\x00")
    with bad.open("rb") as handle:
        response = await auth_client.post(
            f"{DOCUMENTS}/upload", files={"file": (bad.name, handle, "application/octet-stream")}
        )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"


async def test_rejects_empty_file(auth_client: AsyncClient, tmp_path: Path) -> None:
    empty = tmp_path / "vacio.txt"
    empty.write_text("   \n  ", encoding="utf-8")
    with empty.open("rb") as handle:
        response = await auth_client.post(
            f"{DOCUMENTS}/upload", files={"file": (empty.name, handle, "text/plain")}
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] in {"empty_document", "validation_error"}


async def test_upload_requires_authentication(client: AsyncClient, sample_txt: Path) -> None:
    with sample_txt.open("rb") as handle:
        response = await client.post(
            f"{DOCUMENTS}/upload", files={"file": (sample_txt.name, handle, "text/plain")}
        )
    assert response.status_code == 401


async def test_update_and_delete_document(auth_client: AsyncClient, sample_txt: Path) -> None:
    document = await upload(auth_client, sample_txt)

    updated = await auth_client.patch(
        f"{DOCUMENTS}/{document['id']}", json={"title": "Subnetting clase 3"}
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Subnetting clase 3"

    assert (await auth_client.delete(f"{DOCUMENTS}/{document['id']}")).status_code == 200
    assert (await auth_client.get(f"{DOCUMENTS}/{document['id']}")).status_code == 404


async def test_documents_are_private(
    client: AsyncClient, auth_client: AsyncClient, sample_txt: Path, other_user_token: str
) -> None:
    document = await upload(auth_client, sample_txt)
    response = await client.get(
        f"{DOCUMENTS}/{document['id']}", headers={"Authorization": f"Bearer {other_user_token}"}
    )
    assert response.status_code == 404


async def test_search_documents_by_text(auth_client: AsyncClient, sample_txt: Path) -> None:
    await upload(auth_client, sample_txt)
    assert len((await auth_client.get(f"{DOCUMENTS}?search=redes")).json()) == 1
    assert (await auth_client.get(f"{DOCUMENTS}?search=inexistente")).json() == []


# ------------------------------------------------------------------- RAG core
async def test_retrieval_finds_relevant_chunk(
    auth_client: AsyncClient, sample_txt: Path, course_payload: dict
) -> None:
    """RAG must ground the answer in the uploaded document."""
    await upload(auth_client, sample_txt)

    chat = await auth_client.post(
        "/api/v1/ai/chat",
        json={"message": "¿Que mascara de subred usa el prefijo /24?"},
    )
    assert chat.status_code == 200, chat.text
    body = chat.json()
    assert body["used_rag"] is True
    assert body["sources"], "RAG answer must cite at least one source"
    source = body["sources"][0]
    assert source["document_id"] == str(uuid.UUID(source["document_id"]))
    assert source["title"]
    assert "255.255.255.0" in body["message"]


async def test_rag_can_be_disabled(auth_client: AsyncClient, sample_txt: Path) -> None:
    await upload(auth_client, sample_txt)
    body = (
        await auth_client.post(
            "/api/v1/ai/chat", json={"message": "Hola", "use_rag": False}
        )
    ).json()
    assert body["used_rag"] is False
    assert body["sources"] == []


async def test_embeddings_are_deterministic_and_normalised() -> None:
    import numpy as np

    from app.ai.registry import resolve_provider

    provider = (await resolve_provider()).provider
    first = (await provider.embed(["subnetting y mascaras de red"]))[0]
    second = (await provider.embed(["subnetting y mascaras de red"]))[0]

    assert first == second
    assert len(first) == provider.dimensions
    assert abs(float(np.linalg.norm(first)) - 1.0) < 1e-6


async def test_chunking_respects_size_limit() -> None:
    from app.ai.rag.chunking import chunk_text

    text = ("palabra " * 4000).strip()
    chunks = chunk_text(text, chunk_size=400, overlap=60)
    assert len(chunks) > 1
    assert all(len(chunk.content) > 0 for chunk in chunks)
    assert all(len(chunk.content) <= 400 for chunk in chunks)
    assert [chunk.index for chunk in chunks] == list(range(len(chunks)))
    assert chunks[0].char_start == 0
    assert chunks[-1].char_end <= len(text)
