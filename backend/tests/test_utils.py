"""Unit tests for the pieces that are easiest to get subtly wrong."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import numpy as np
import pytest

from app.ai.rag.chunking import chunk_text
from app.ai.rag.parsing import coerce_bool, coerce_float, coerce_int, ensure_list, extract_json
from app.ai.rag.vectorstore import cosine_similarity
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.utils.text import (
    excerpt,
    fold_accents,
    keyword_scores,
    normalize_text,
    slugify,
    split_paragraphs,
    split_sentences,
    tokenize,
    word_count,
)


class TestText:
    def test_tokenize_drops_accents_and_punctuation(self) -> None:
        assert tokenize("Álgebra, ¡lineal! ¿y más?") == ["algebra", "lineal", "y", "mas"]

    def test_tokenize_splits_slashed_and_dotted_tokens(self) -> None:
        assert tokenize("Protocolo TCP/IP v4.1") == ["protocolo", "tcp", "ip", "v4", "1"]

    def test_tokenize_keeps_hyphenated_tokens(self) -> None:
        assert tokenize("use-case study") == ["use-case", "study"]

    def test_fold_accents_is_idempotent_and_keeps_case(self) -> None:
        assert fold_accents(fold_accents("Diseño")) == fold_accents("Diseño")
        assert fold_accents("Diseño") == "Diseno"
        assert fold_accents("máscara") == "mascara"

    def test_normalize_collapses_whitespace_but_keeps_case(self) -> None:
        assert normalize_text("  Hola   MUNDO \n") == "Hola MUNDO"
        assert normalize_text("uno\n\n\n\ndos") == "uno\n\ndos"

    def test_split_sentences_splits_on_terminators(self) -> None:
        assert split_sentences("Uno. Dos tres! Cuatro?") == ["Uno.", "Dos tres!", "Cuatro?"]

    def test_split_sentences_keeps_interior_punctuation(self) -> None:
        assert split_sentences("Uno. Dos; tres! Cuatro?") == ["Uno.", "Dos; tres!", "Cuatro?"]

    def test_split_sentences_keeps_unterminated_tail(self) -> None:
        assert split_sentences("Uno. Sin punto final") == ["Uno.", "Sin punto final"]

    def test_split_paragraphs_drops_empty_blocks(self) -> None:
        assert split_paragraphs("Uno\n\n\n\nDos\n\n") == ["Uno", "Dos"]

    def test_excerpt_truncates_with_ellipsis(self) -> None:
        assert excerpt("a" * 400, 50).endswith("…")
        assert len(excerpt("a" * 400, 50)) <= 50

    def test_excerpt_returns_short_text_untouched(self) -> None:
        assert excerpt("corto", 50) == "corto"

    def test_word_count_ignores_punctuation(self) -> None:
        assert word_count("Hola, mundo! ¿Estas bien?") == 4

    def test_slugify_produces_url_safe_text(self) -> None:
        assert slugify("Álgebra Lineal — Űnico") == "algebra-lineal-unico"

    def test_keyword_scores_ranks_frequent_terms_first(self) -> None:
        scores = keyword_scores("red red red subnetting subnetting tcp", top_k=3)
        assert [word for word, _ in scores][:2] == ["red", "subnetting"]
        assert scores[0][1] > scores[-1][1]

    def test_keyword_scores_on_empty_text(self) -> None:
        assert keyword_scores("   ") == []


class TestJsonParsing:
    def test_extract_json_from_surrounding_prose(self) -> None:
        assert extract_json('Listo: {"ok": true} — listo.') == {"ok": True}

    def test_extract_json_from_fenced_block(self) -> None:
        assert extract_json('```json\n{"a": [1, 2]}\n```') == {"a": [1, 2]}

    def test_extract_json_unwraps_trailing_comma(self) -> None:
        assert extract_json('{"a": 1, "b": [1, 2,],}') == {"a": 1, "b": [1, 2]}

    def test_extract_json_handles_smart_quotes(self) -> None:
        assert extract_json('{“a”: 1}') == {"a": 1}

    def test_extract_json_rejects_garbage(self) -> None:
        with pytest.raises(ValueError):
            extract_json("sin json whatsoever")

    def test_ensure_list_unwraps_a_keyed_container(self) -> None:
        assert ensure_list({"questions": [{"a": 1}, {"b": 2}]}) == [{"a": 1}, {"b": 2}]

    def test_ensure_list_keeps_plain_lists(self) -> None:
        assert ensure_list([{"a": 1}]) == [{"a": 1}]

    def test_ensure_list_drops_none_and_non_dict_entries(self) -> None:
        assert ensure_list([{"a": 1}, None, "basura"]) == [{"a": 1}]

    def test_ensure_list_on_scalars_and_none(self) -> None:
        assert ensure_list(None) == []
        assert ensure_list("uno") == []
        assert ensure_list(7) == []

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("4.5", 4.5), (3, 3.0), (None, 0.0), ("nope", 0.0), (True, 1.0)],
    )
    def test_coerce_float(self, value: object, expected: float) -> None:
        assert coerce_float(value) == pytest.approx(expected)

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("4.9", 4), (5, 5), (None, 0), ("x", 0), (2.4, 2)],
    )
    def test_coerce_int(self, value: object, expected: int) -> None:
        assert coerce_int(value) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("sí", True), (True, True), ("false", False), (0, False), (None, False)],
    )
    def test_coerce_bool(self, value: object, expected: bool) -> None:
        assert coerce_bool(value) is expected


class TestSecurity:
    def test_password_hash_roundtrip(self) -> None:
        hashed = hash_password("secreto123")
        assert hashed != "secreto123"
        assert verify_password("secreto123", hashed)
        assert not verify_password("otro", hashed)

    def test_hashes_are_salted(self) -> None:
        assert hash_password("igual") != hash_password("igual")

    def test_passwords_longer_than_the_bcrypt_limit_are_pre_hashed(self) -> None:
        long_password = "a" * 200
        assert verify_password(long_password, hash_password(long_password))

    def test_verify_rejects_malformed_hash(self) -> None:
        assert verify_password("x", "not-a-hash") is False

    def test_access_token_roundtrip(self) -> None:
        from app.core.security import decode_token

        payload = decode_token(create_access_token("user-1"))
        assert payload["sub"] == "user-1"
        assert payload["type"] == "access"

    def test_access_token_accepts_uuid_subject(self) -> None:
        import uuid

        from app.core.security import decode_token

        identifier = uuid.uuid4()
        assert decode_token(create_access_token(identifier))["sub"] == str(identifier)

    def test_refresh_token_cannot_be_used_as_access_token(self) -> None:
        from app.core.security import decode_token

        with pytest.raises(TokenError):
            decode_token(create_refresh_token("user-1"))

    def test_decode_rejects_tampered_token(self) -> None:
        from app.core.security import decode_token

        token = create_access_token("user-1")
        with pytest.raises(TokenError):
            decode_token(token[:-2] + "xx")

    def test_decode_rejects_garbage(self) -> None:
        from app.core.security import decode_token

        with pytest.raises(TokenError):
            decode_token("no.es.un.jwt")

    def test_decode_rejects_expired_token(self) -> None:
        from app.core.security import _create_token, decode_token

        expired = _create_token("user-1", "access", timedelta(seconds=-10))
        with pytest.raises(TokenError):
            decode_token(expired)


class TestVectorMath:
    def test_identical_vectors_score_one(self) -> None:
        scores = cosine_similarity(np.array([1.0, 2.0, 3.0]), np.array([[1.0, 2.0, 3.0]]))
        assert scores.tolist() == pytest.approx([1.0])

    def test_orthogonal_vectors_score_zero(self) -> None:
        scores = cosine_similarity(np.array([1.0, 0.0]), np.array([[0.0, 1.0]]))
        assert scores.tolist() == pytest.approx([0.0])

    def test_opposite_vectors_score_minus_one(self) -> None:
        scores = cosine_similarity(np.array([1.0, 0.0]), np.array([[-1.0, 0.0]]))
        assert scores.tolist() == pytest.approx([-1.0])

    def test_empty_matrix_returns_no_scores(self) -> None:
        assert cosine_similarity(np.array([1.0, 0.0]), np.zeros((0, 2))).tolist() == []

    def test_zero_query_vector_is_safe(self) -> None:
        scores = cosine_similarity(np.zeros(2), np.array([[1.0, 1.0]]))
        assert scores.tolist() == pytest.approx([0.0])

    def test_zero_matrix_rows_do_not_divide_by_zero(self) -> None:
        scores = cosine_similarity(np.array([1.0, 0.0]), np.array([[0.0, 0.0], [1.0, 0.0]]))
        assert scores.tolist() == pytest.approx([0.0, 1.0])


class TestChunking:
    def test_short_document_becomes_one_chunk(self) -> None:
        chunks = chunk_text("Un solo parrafo corto.", chunk_size=500, overlap=50)
        assert len(chunks) == 1
        assert chunks[0].index == 0
        assert chunks[0].token_estimate > 0

    def test_long_document_is_split_and_indexes_are_sequential(self) -> None:
        text = "\n\n".join(f"Seccion {i}. " + ("palabra " * 80) for i in range(12))
        chunks = chunk_text(text, chunk_size=400, overlap=40)
        assert len(chunks) > 1
        assert [chunk.index for chunk in chunks] == list(range(len(chunks)))

    def test_oversized_sentence_is_hard_split(self) -> None:
        chunks = chunk_text("a" * 3000, chunk_size=500, overlap=20)
        assert len(chunks) > 1
        assert all(len(chunk.content) <= 520 for chunk in chunks)

    def test_chunks_carry_the_nearest_heading(self) -> None:
        text = "Protocolos\n" + ("contenido de la seccion " * 60) + "\nARP\n" + ("mas texto " * 60)
        chunks = chunk_text(text, chunk_size=300, overlap=30)
        headings = {chunk.heading for chunk in chunks}
        assert headings & {"Protocolos", "ARP"}

    def test_empty_document_yields_nothing(self) -> None:
        assert chunk_text("   ", chunk_size=400, overlap=20) == []


class TestLocalProvider:
    async def test_embeddings_are_deterministic(self) -> None:
        from app.ai.providers.local import LocalProvider

        provider = LocalProvider()
        assert await provider.embed_one("TCP es fiable") == await provider.embed_one("TCP es fiable")
        assert await provider.embed_one("TCP es fiable") != await provider.embed_one("UDP es rapido")

    async def test_embeddings_are_normalised(self) -> None:
        from app.ai.providers.local import LocalProvider

        vector = await LocalProvider().embed_one("subnetting")
        assert sum(value * value for value in vector) == pytest.approx(1.0, abs=1e-5)

    async def test_similar_text_scores_higher_than_unrelated_text(self) -> None:
        from app.ai.providers.local import LocalProvider
        from app.ai.rag.vectorstore import cosine_similarity

        provider = LocalProvider()
        query = np.array(await provider.embed_one("subnetting y mascara de subred"))
        matrix = np.array(
            await provider.embed(
                [
                    "Subnetting divide una red IP usando una mascara de subred",
                    "El protocolo ARP resuelve direcciones IP a direcciones MAC",
                ]
            )
        )
        scores = cosine_similarity(query, matrix)
        assert scores[0] > scores[1]

    async def test_empty_batch_is_handled(self) -> None:
        from app.ai.providers.local import LocalProvider

        assert await LocalProvider().embed([]) == []


class TestHealth:
    async def test_local_provider_is_reported_ready(self) -> None:
        from app.ai.registry import get_health

        health = await get_health(force=True)
        assert health.provider == "local"
        assert health.available is True
        assert health.embedding_model

    async def test_health_is_stable_across_calls(self) -> None:
        from app.ai.registry import get_health

        await get_health(force=True)
        cached = await get_health()
        fresh = await get_health(force=True)
        assert cached.provider == fresh.provider
        assert cached.available is fresh.available


class TestUtcHelpers:
    def test_utcnow_is_aware(self) -> None:
        from app.db.base import utcnow

        value = utcnow()
        assert value.tzinfo is not None
        assert value.utcoffset() == timedelta(0)

    def test_naive_datetimes_come_back_utc_aware(self) -> None:
        from sqlalchemy import Column, MetaData, Table

        from app.db.base import UTCDateTime

        table = Table("t", MetaData(), Column("when", UTCDateTime))
        naive = datetime(2026, 3, 1, 12, 0)
        restored = table.c.when.type.process_result_value(
            table.c.when.type.process_bind_param(naive, None), None
        )
        assert restored == naive.replace(tzinfo=UTC)
        assert restored.utcoffset() == timedelta(0)

    def test_aware_datetimes_are_normalised_to_utc_on_write(self) -> None:
        from sqlalchemy import Column, MetaData, Table

        from app.db.base import UTCDateTime

        table = Table("t", MetaData(), Column("when", UTCDateTime))
        local = datetime(2026, 3, 1, 12, 0, tzinfo=timezone(timedelta(hours=-5)))
        stored = table.c.when.type.process_bind_param(local, None)
        assert stored.utcoffset() == timedelta(0)
        assert stored.hour == 17
