"""Error envelope and standard error codes."""

from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    field: str | None = None
    reason: str | None = None
    extra: dict[str, Any] | None = None


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class ApiError(HTTPException):
    """Carries a structured `ErrorBody` and an HTTP status code."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        body = ErrorBody(code=code, message=message, details=details or [])
        super().__init__(status_code=status_code, detail=body.model_dump())
        self.envelope = ErrorEnvelope(error=body)


def not_found(code: str, message: str) -> ApiError:
    return ApiError(404, code, message)


def validation_failed(message: str, details: list[ErrorDetail] | None = None) -> ApiError:
    return ApiError(400, "validation_failed", message, details)


def forbidden(message: str) -> ApiError:
    return ApiError(403, "forbidden", message)


def conflict(message: str) -> ApiError:
    return ApiError(409, "conflict", message)
