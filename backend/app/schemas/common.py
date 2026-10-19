"""Shared response primitives."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PageMeta(BaseModel):
    total: int = Field(description="Total number of matching records")
    limit: int
    offset: int
    has_more: bool


class Page(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta


class ErrorBody(BaseModel):
    code: str = Field(examples=["not_found"])
    message: str = Field(examples=["The requested resource does not exist."])
    path: str | None = None
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class OperationResult(BaseModel):
    """Result of a mutation that is not a full entity (e.g. quiz grading)."""

    success: bool = True
    score: float | None = None
    details: dict | None = None