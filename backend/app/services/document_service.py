"""Document ingestion pipeline.

PDF/DOCX/TXT → validate → extract → chunk → embed → persist → indexable.
Failures after the file is stored are recorded on the row (`status=failed`)
instead of losing the upload.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Sequence
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.ai.base import AIProvider
from app.ai.rag.chunking import chunk_text
from app.ai.rag.vectorstore import VectorStore
from app.core.config import settings
from app.core.errors import (
    AIProviderError,
    NotFoundError,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
    ValidationError,
)
from app.core.logging import get_logger
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.models.user import User
from app.repositories.courses import CourseRepository
from app.repositories.documents import DocumentRepository
from app.schemas.document import DocumentDetail, DocumentRead, DocumentUpdate
from app.utils.text import excerpt, normalize_text
from app.utils.text_extraction import extract_text

logger = get_logger("app.documents")

_EMBED_BATCH = 16
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class DocumentService:
    def __init__(self, db: Session, user: User, provider: AIProvider) -> None:
        self.db = db
        self.user = user
        self.provider = provider
        self.repo = DocumentRepository(db)
        self.courses = CourseRepository(db)
        self.upload_dir = settings.resolved_upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------- uploads
    async def upload(
        self, file: UploadFile, *, course_id: uuid.UUID | None = None, title: str | None = None
    ) -> DocumentRead:
        filename = (file.filename or "").strip()
        if not filename:
            raise ValidationError("The file has no name.", code="missing_filename")

        extension = Path(filename).suffix.lower()
        if extension not in settings.allowed_extension_list:
            raise UnsupportedMediaTypeError(
                f"STUDIA AI accepts {', '.join(settings.allowed_extension_list)} files.",
                details={"extension": extension},
            )

        payload = await file.read()
        await file.close()
        if not payload:
            raise ValidationError("The uploaded file is empty.", code="empty_file")
        if len(payload) > settings.max_upload_bytes:
            raise PayloadTooLargeError(
                f"Files must be smaller than {settings.max_upload_mb} MB.",
                details={"size_bytes": len(payload), "max_bytes": settings.max_upload_bytes},
            )

        if course_id is not None and self.courses.get_enrollment(self.user.id, course_id) is None:
            raise ValidationError("You are not enrolled in that course.", code="course_not_accessible")

        stored_name = self._store(payload, extension)
        document = Document(
            user_id=self.user.id,
            course_id=course_id,
            title=(title or Path(filename).stem).strip()[:255],
            filename=filename[:255],
            stored_name=stored_name,
            content_type=file.content_type or _guess_content_type(extension),
            extension=extension,
            size_bytes=len(payload),
            status=DocumentStatus.PROCESSING,
        )
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        try:
            await self._ingest(document, Path(self.upload_dir / stored_name))
        except (ValidationError, UnsupportedMediaTypeError, PayloadTooLargeError):
            self._mark_failed(document, "The file could not be processed.")
            raise
        except AIProviderError:
            # Text is fine, only the vectors are missing: keep the document.
            document.status = DocumentStatus.READY
            document.error_message = "Embeddings unavailable — search will fall back to keywords."
            self.db.commit()
            self.db.refresh(document)
            return self._to_read(document)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ingestion failed for %s", document.filename)
            self._mark_failed(document, f"Unexpected error while processing the file: {exc}")
            raise ValidationError("We could not process this file. Please try another file.") from exc

        return self.get(document.id)

    def _store(self, payload: bytes, extension: str) -> str:
        safe = _SAFE_NAME.sub("_", f"{uuid.uuid4().hex[:12]}{extension}")
        target = self.upload_dir / f"{self.user.id.hex[:8]}_{safe}"
        target.write_bytes(payload)
        return target.name

    async def _ingest(self, document: Document, path: Path) -> None:
        extracted = extract_text(path, document.extension)
        document.page_count = extracted.page_count
        document.char_count = extracted.char_count
        document.word_count = extracted.word_count
        document.detected_language = _guess_language(extracted.text)

        chunks = chunk_text(extracted.text)
        if not chunks:
            raise ValidationError(
                "No usable text was found in this document.", code="empty_document"
            )

        embeddings = await self._embed(chunks)
        VectorStore(self.db, self.user.id).delete_document(document.id)
        VectorStore(self.db, self.user.id).add(
            document_id=document.id,
            chunks=[
                {
                    "chunk_index": chunk.index,
                    "content": chunk.content,
                    "char_start": chunk.char_start,
                    "char_end": chunk.char_end,
                    "heading": chunk.heading,
                    "page_number": chunk.page_number,
                    "token_estimate": chunk.token_estimate,
                    "embedding": embeddings[index],
                }
                for index, chunk in enumerate(chunks)
            ],
            embedding_model=self.provider.embedding_model_name,
        )

        document.chunk_count = len(chunks)
        document.summary = _auto_summary(extracted.text)
        document.topics = _auto_topics(extracted.text)
        document.status = DocumentStatus.READY
        document.error_message = extracted.warnings[0] if extracted.warnings else None
        self.db.commit()
        self.db.refresh(document)

    async def _embed(self, chunks: Sequence) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(chunks), _EMBED_BATCH):
            batch = [chunk.content[:4000] for chunk in chunks[start : start + _EMBED_BATCH]]
            vectors.extend(await self.provider.embed(batch))
        return vectors

    def _mark_failed(self, document: Document, message: str) -> None:
        document.status = DocumentStatus.FAILED
        document.error_message = message[:500]
        self.db.commit()

    # ---------------------------------------------------------------- read
    def list(
        self,
        *,
        course_id: uuid.UUID | None = None,
        status: DocumentStatus | None = None,
        search: str | None = None,
    ) -> list[DocumentRead]:
        rows = self.repo.list_for_user(
            self.user.id, course_id=course_id, status=status, search=search
        )
        return [self._to_read(row) for row in rows]

    def get(self, document_id: uuid.UUID) -> DocumentRead:
        return self._to_read(self._require(document_id))

    def detail(self, document_id: uuid.UUID) -> DocumentDetail:
        document = self._require(document_id)
        chunks = self.repo.chunks(document.id, limit=25)
        return DocumentDetail(
            **self._to_read(document).model_dump(),
            preview=self._preview(document),
            chunks=[
                {
                    "id": chunk.id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "content": excerpt(chunk.content, 600),
                    "page_number": chunk.page_number,
                    "heading": chunk.heading,
                    "token_estimate": chunk.token_estimate,
                }
                for chunk in chunks
            ],
        )

    def update(self, document_id: uuid.UUID, payload: DocumentUpdate) -> DocumentRead:
        document = self._require(document_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            if (
                field == "course_id"
                and value is not None
                and self.courses.get_enrollment(self.user.id, value) is None
            ):
                raise ValidationError("You are not enrolled in that course.")
            setattr(document, field, value)
        self.db.commit()
        self.db.refresh(document)
        return self._to_read(document)

    def delete(self, document_id: uuid.UUID) -> None:
        document = self._require(document_id)
        path = self.upload_dir / document.stored_name
        VectorStore(self.db, self.user.id).delete_document(document.id)
        self.db.delete(document)
        self.db.commit()
        path.unlink(missing_ok=True)

    def require_documents(self, document_ids: list[uuid.UUID]) -> list[Document]:
        found = self.repo.get_many_owned(self.user.id, document_ids)
        missing = set(document_ids) - {document.id for document in found}
        if missing:
            raise NotFoundError(
                "One or more selected documents are not available.",
                code="documents_not_found",
                details={"missing": [str(item) for item in missing]},
            )
        return found

    # ------------------------------------------------------------- helpers
    def _require(self, document_id: uuid.UUID) -> Document:
        document = self.repo.get_owned(self.user.id, document_id)
        if document is None:
            raise NotFoundError("That document does not exist.", code="document_not_found")
        return document

    def _preview(self, document: Document) -> str | None:
        chunks = self.repo.chunks(document.id, limit=2)
        return excerpt(" ".join(chunk.content for chunk in chunks), 600) if chunks else None

    def _to_read(self, document: Document) -> DocumentRead:
        return DocumentRead(
            **{
                "id": document.id,
                "title": document.title,
                "filename": document.filename,
                "content_type": document.content_type,
                "extension": document.extension,
                "size_bytes": document.size_bytes,
                "page_count": document.page_count,
                "word_count": document.word_count,
                "char_count": document.char_count,
                "chunk_count": document.chunk_count,
                "status": document.status,
                "error_message": document.error_message,
                "detected_language": document.detected_language,
                "summary": document.summary,
                "topics": document.topics,
                "course_id": document.course_id,
                "course": document.course,
                "created_at": document.created_at,
                "updated_at": document.updated_at,
            }
        )


def _guess_content_type(extension: str) -> str:
    return {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
    }.get(extension, "application/octet-stream")


def _guess_language(text: str) -> str:
    sample = text[:2000].lower()
    spanish = sum(sample.count(word) for word in (" de ", " la ", " el ", " los ", " que ", " para "))
    english = sum(sample.count(word) for word in (" the ", " and ", " of ", " to ", " with "))
    return "es" if spanish >= english else "en"


def _auto_summary(text: str) -> str:
    from app.utils.text import keyword_scores, split_sentences

    sentences = split_sentences(text)
    if not sentences:
        return None
    weights = dict(keyword_scores(text, top_k=30))
    scored = [
        (sum(weights.get(word, 0.0) for word in sentence.lower().split()), index, sentence)
        for index, sentence in enumerate(sentences[:40])
    ]
    scored.sort(key=lambda item: -item[0])
    best = sorted(scored[:2], key=lambda item: item[1])
    return excerpt(" ".join(sentence for _, _, sentence in best), 480)


def _auto_topics(text: str) -> list[str]:
    from app.utils.text import keyword_scores

    return [term for term, _ in keyword_scores(normalize_text(text), top_k=6)]