"""Vector store over `document_chunks`.

`VectorStore` keeps the persistence concern in one place so swapping the JSON
column for a native `pgvector` column is a single-file change.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import DocumentChunk


@dataclass
class ScoredChunk:
    chunk: DocumentChunk
    score: float

    @property
    def content(self) -> str:
        return self.chunk.content


def cosine_similarity(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return np.zeros(0, dtype=np.float32)
    query_norm = np.linalg.norm(query)
    if query_norm == 0:
        return np.zeros(matrix.shape[0], dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1)
    norms[norms == 0] = 1.0
    return (matrix @ query) / (norms * query_norm)


class VectorStore:
    """Similarity search restricted to one user's documents."""

    def __init__(self, db: Session, user_id: uuid.UUID) -> None:
        self.db = db
        self.user_id = user_id

    def add(
        self,
        *,
        document_id: uuid.UUID,
        chunks: list[dict],
        embedding_model: str,
    ) -> list[DocumentChunk]:
        rows: list[DocumentChunk] = []
        for payload in chunks:
            row = DocumentChunk(
                document_id=document_id,
                user_id=self.user_id,
                chunk_index=payload["chunk_index"],
                content=payload["content"],
                char_start=payload.get("char_start", 0),
                char_end=payload.get("char_end", 0),
                page_number=payload.get("page_number"),
                heading=payload.get("heading"),
                token_estimate=payload.get("token_estimate", 0),
                embedding=payload.get("embedding"),
                embedding_model=embedding_model,
            )
            rows.append(row)
        self.db.add_all(rows)
        self.db.flush()
        return rows

    def delete_document(self, document_id: uuid.UUID) -> int:
        rows = self.db.scalars(
            select(DocumentChunk).where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.user_id == self.user_id,
            )
        ).all()
        for row in rows:
            self.db.delete(row)
        self.db.flush()
        return len(rows)

    def search(
        self,
        embedding: list[float],
        *,
        document_ids: list[uuid.UUID] | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[ScoredChunk]:
        statement = select(DocumentChunk).where(DocumentChunk.user_id == self.user_id)
        if document_ids:
            statement = statement.where(DocumentChunk.document_id.in_(document_ids))
        rows = self.db.scalars(statement).all()
        return self.rank(embedding, rows, top_k=top_k, min_score=min_score)

    def search_many(
        self,
        embeddings: list[list[float]],
        *,
        document_ids: list[uuid.UUID] | None = None,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list[ScoredChunk]:
        statement = select(DocumentChunk).where(DocumentChunk.user_id == self.user_id)
        if document_ids:
            statement = statement.where(DocumentChunk.document_id.in_(document_ids))
        rows = self.db.scalars(statement).all()
        merged: dict[uuid.UUID, ScoredChunk] = {}
        for embedding in embeddings:
            for scored in self.rank(embedding, rows, top_k=top_k, min_score=min_score):
                existing = merged.get(scored.chunk.id)
                if existing is None or scored.score > existing.score:
                    merged[scored.chunk.id] = scored
        return sorted(merged.values(), key=lambda item: -item.score)[:top_k]

    @staticmethod
    def rank(
        embedding: list[float],
        rows: list[DocumentChunk],
        *,
        top_k: int,
        min_score: float,
    ) -> list[ScoredChunk]:
        if not rows:
            return []
        usable = [row for row in rows if row.embedding]
        if not usable:
            return []

        matrix = np.asarray([row.embedding for row in usable], dtype=np.float32)
        if matrix.shape[1] != len(embedding):
            # Embedding model changed: skip mismatched vectors instead of failing.
            usable = [row for row in usable if row.embedding and len(row.embedding) == len(embedding)]
            if not usable:
                return []
            matrix = np.asarray([row.embedding for row in usable], dtype=np.float32)

        scores = cosine_similarity(np.asarray(embedding, dtype=np.float32), matrix)
        ranked = [
            ScoredChunk(chunk=row, score=float(score))
            for row, score in zip(usable, scores, strict=True)
            if float(score) >= min_score
        ]
        ranked.sort(key=lambda item: (-item.score, item.chunk.chunk_index))
        return ranked[:top_k]

    def count(self, document_ids: list[uuid.UUID] | None = None) -> int:
        statement = select(DocumentChunk.id).where(DocumentChunk.user_id == self.user_id)
        if document_ids:
            statement = statement.where(DocumentChunk.document_id.in_(document_ids))
        return len(self.db.scalars(statement).all())

    @staticmethod
    def stale_before(cutoff: datetime) -> datetime:
        return cutoff.astimezone(UTC) if cutoff.tzinfo else cutoff.replace(tzinfo=UTC)