"""Domain exceptions and the global FastAPI exception handlers.

Rule enforced here: a client never receives a bare `500 Internal Server Error`.
Every failure maps to a stable machine readable `error.code` plus a human
readable message.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger("app.errors")

# Starlette renamed these constants; resolve defensively so the app works on
# both older and newer versions without deprecation warnings.
HTTP_422 = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
HTTP_413 = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413)


class AppError(Exception):
    """Base class for every expected domain error."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "bad_request"
    message: str = "The request could not be processed."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    message = "The requested resource does not exist."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"
    message = "The resource already exists or conflicts with existing data."


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"
    message = "You must sign in to continue."


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"
    message = "You do not have access to this resource."


class ValidationError(AppError):
    status_code = HTTP_422
    code = "validation_error"
    message = "Some of the provided values are not valid."


class PayloadTooLargeError(AppError):
    status_code = HTTP_413
    code = "payload_too_large"
    message = "The uploaded file exceeds the maximum allowed size."


class UnsupportedMediaTypeError(AppError):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    code = "unsupported_media_type"
    message = "That file type is not supported."


class AIProviderError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "ai_provider_unavailable"
    message = "The AI provider is unavailable right now. Please try again."


class AIResponseError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "ai_invalid_response"
    message = "The AI provider returned an unusable response."


def _payload(
    *,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    request: Request | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            **({"details": details} if details else {}),
        }
    }
    if request is not None:
        body["error"]["path"] = request.url.path
    return body


def register_exception_handlers(app: FastAPI) -> None:
    """Attach every handler exactly once."""

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("%s on %s: %s", exc.code, request.url.path, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(
                code=exc.code, message=exc.message, details=exc.details, request=request
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "http_error"
        message = {
            401: "You must sign in to continue.",
            403: "You do not have access to this resource.",
            404: "That endpoint or resource does not exist.",
            405: "That method is not allowed for this endpoint.",
        }.get(exc.status_code, str(exc.detail))
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(code=code, message=message, request=request),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, str] = {}
        for error in exc.errors():
            location = [str(part) for part in error["loc"] if part not in ("body", "query")]
            fields[".".join(location) or "body"] = error.get("msg", "Invalid value")
        return JSONResponse(
            status_code=HTTP_422,
            content=_payload(
                code="validation_error",
                message="Please review the highlighted fields and try again.",
                details={"fields": fields},
                request=request,
            ),
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Integrity error on %s: %s", request.url.path, exc.orig)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_payload(
                code="conflict",
                message="That value is already in use or breaks a data relationship.",
                request=request,
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Database failure on %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=_payload(
                code="database_unavailable",
                message="We could not reach the academic database. Please retry in a moment.",
                request=request,
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_payload(
                code="internal_error",
                message=(
                    "Something went wrong on our side. The incident has been logged."
                    if settings_is_production()
                    else f"{type(exc).__name__}: {exc}"
                ),
                request=request,
            ),
        )


def settings_is_production() -> bool:
    from app.core.config import settings

    return settings.is_production