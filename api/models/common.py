"""Common models used across endpoints."""

from pydantic import BaseModel
from typing import Optional, List, Any


class ErrorDetail(BaseModel):
    """Error detail model."""
    code: str
    message: str
    details: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: ErrorDetail


class PaginationParams(BaseModel):
    """Pagination parameters."""
    limit: int = 50
    offset: int = 0


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    total: int
    limit: int
    offset: int
