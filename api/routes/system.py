"""System endpoints (health check, etc.)."""

from fastapi import APIRouter
from api.models.common import ErrorResponse

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status and version information
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "database": "connected",  # TODO: Actually check database
        "cache_stats": {
            "total_entries": 0,  # TODO: Get from cache manager
            "total_size_mb": 0.0
        },
        "ai_service": "available"  # TODO: Check AI service availability
    }
