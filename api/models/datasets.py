"""Dataset models."""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DatasetCreate(BaseModel):
    """Dataset creation model."""
    name: Optional[str] = None
    source_type: Optional[str] = None  # Auto-detected if not provided


class DatasetResponse(BaseModel):
    """Dataset response model."""
    dataset_id: str
    name: str
    source_type: str
    status: str
    row_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class DatasetListResponse(BaseModel):
    """Dataset list response."""
    datasets: list[DatasetResponse]
    total: int
    limit: int
    offset: int
