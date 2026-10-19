"""Retriever: hybrid semantic + lexical search with citations."""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.rag.vectorstore import ScoredChunk, VectorStore
from app.core.config import settings
from app.models.document import Document
from app.schemas.document import SourceCitation
from app.utils.text import content_words, excerpt, split_sentences


@dataclass
class RetrievedChunk:
    """An immutable retrieval hit: the DB row plus the focused excerpt."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    score: float
    chunk_index: int
    page_number: int | None = None
    heading: str | None = None


@dataclass
class RetrievedContext:
    query: str
    chunks: list[RetrievedChunk]
    sources: list[SourceCitation]
    used_rag: bool

    @property
    def context_text(self) -> str:
        if not self.chunks:
            return ""
        blocks: list[str] = []
        for position, chunk in enumerate(self.chunks, start=1):
            label = chunk.heading or f"fragmento {chunk.chunk_index + 1}"
            if chunk.page_number:
                label = f"{label} (p. {chunk.page_number})"
            blocks.append(f"[{position}] {label}\n{chunk.content}")
        return "\n\n---\n\n".join(blocks)


class Retriever:
    def __init__(self, db: Session, provider: AIProvider, user_id: uuid.UUID) -> None:
        self.db = db
        self.provider = provider
        self.store = VectorStore(db, user_id)

    async def retrieve(
        self,
        query: str,
        *,
        document_ids: list[uuid.UUID] | None = None,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> RetrievedContext:
        top_k = top_k or settings.rag_top_k
        min_score = settings.rag_min_score if min_score is None else min_score

        if not self.store.count(document_ids):
            return RetrievedContext(query=query, chunks=[], sources=[], used_rag=False)

        embedding = await self.provider.embed_one(query)
        semantic = self.store.search(
            embedding, document_ids=document_ids, top_k=top_k * 3, min_score=0.0
        )
        hits = self._hybrid_rank(query, semantic, top_k=top_k, min_score=min_score)
        sources = self._citations(hits)
        return RetrievedContext(query=query, chunks=hits, sources=sources, used_rag=bool(hits))

    def _hybrid_rank(
        self, query: str, semantic: list[ScoredChunk], *, top_k: int, min_score: float
    ) -> list[RetrievedChunk]:
        """Blend vector similarity with a lexical overlap signal."""
        if not semantic:
            return []
        keywords = set(content_words(query))
        hits: list[RetrievedChunk] = []
        for scored in semantic:
            words = set(content_words(scored.content))
            overlap = len(keywords & words) / math.sqrt(len(words) or 1)
            combined = 0.72 * scored.score + 0.28 * min(overlap * 3, 1.0)
            if combined < min_score:
                continue
            chunk = scored.chunk
            hits.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    content=_focus(chunk.content, keywords),
                    score=round(combined, 4),
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    heading=chunk.heading,
                )
            )
        hits.sort(key=lambda item: -item.score)
        return hits[:top_k]

    def _citations(self, hits: list[RetrievedChunk]) -> list[SourceCitation]:
        if not hits:
            return []
        document_ids = list({hit.document_id for hit in hits})
        documents = {
            document.id: document
            for document in self.db.scalars(
                select(Document).where(Document.id.in_(document_ids))
            ).all()
        }
        citations: list[SourceCitation] = []
        for hit in hits:
            document = documents.get(hit.document_id)
            if document is None:
                continue
            citations.append(
                SourceCitation(
                    document_id=document.id,
                    title=document.title,
                    filename=document.filename,
                    chunk_index=hit.chunk_index,
                    page_number=hit.page_number,
                    score=hit.score,
                    excerpt=excerpt(hit.content, 220),
                )
            )
        return citations


def _focus(content: str, keywords: set[str], *, max_sentences: int = 3) -> str:
    """Return the query-relevant sentences of a chunk (never mutates the row)."""
    sentences = split_sentences(content)
    if len(sentences) <= max_sentences or not keywords:
        return content
    ranked = sorted(
        enumerate(sentences),
        key=lambda pair: -sum(1 for word in content_words(pair[1]) if word in keywords),
    )
    keep = sorted(index for index, _ in ranked[:max_sentences])
    return " ".join(sentences[index] for index in keep)