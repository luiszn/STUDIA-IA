"""Document endpoints (upload, listing, RAG-ready detail)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.ai.registry import resolve_provider
from app.api.deps import CurrentUser, DbSession
from app.models.enums import DocumentStatus
from app.schemas.common import MessageResponse
from app.schemas.document import DocumentDetail, DocumentRead, DocumentUpdate
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


async def _service(db, user) -> DocumentService:
    resolved = await resolve_provider()
    return DocumentService(db, user, resolved.provider)


@router.get("", response_model=list[DocumentRead], summary="List my documents")
async def list_documents(
    user: CurrentUser,
    db: DbSession,
    course_id: uuid.UUID | None = None,
    document_status: DocumentStatus | None = Query(default=None, alias="status"),
    search: str | None = None,
) -> list[DocumentRead]:
    service = await _service(db, user)
    return service.list(course_id=course_id, status=document_status, search=search)


@router.post(
    "/upload",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and index a PDF / DOCX / TXT document",
)
async def upload_document(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(..., description="PDF, DOCX or TXT file"),
    course_id: uuid.UUID | None = Form(default=None),
    title: str | None = Form(default=None),
) -> DocumentRead:
    service = await _service(db, user)
    return await service.upload(file, course_id=course_id, title=title)


@router.get("/{document_id}", response_model=DocumentDetail, summary="Document detail and chunks")
async def get_document(document_id: uuid.UUID, user: CurrentUser, db: DbSession) -> DocumentDetail:
    service = await _service(db, user)
    return service.detail(document_id)


@router.patch("/{document_id}", response_model=DocumentRead, summary="Update document metadata")
async def update_document(
    document_id: uuid.UUID, payload: DocumentUpdate, user: CurrentUser, db: DbSession
) -> DocumentRead:
    service = await _service(db, user)
    return service.update(document_id, payload)


@router.delete("/{document_id}", response_model=MessageResponse, summary="Delete a document")
async def delete_document(
    document_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> MessageResponse:
    service = await _service(db, user)
    service.delete(document_id)
    return MessageResponse(message="Document deleted.")