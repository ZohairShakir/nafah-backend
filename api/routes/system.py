"""System endpoints (health check, etc.)."""

import os
from fastapi import APIRouter
from api.models.common import ErrorResponse
from storage.database import Database
from storage.cache import CacheManager

router = APIRouter(prefix="/api/v1", tags=["system"])

DB_PATH = os.getenv("DATABASE_PATH", "data/nafah.db")


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status and version information
    """
    # Check database connection
    db_status = "connected"
    try:
        db = Database(DB_PATH)
        # Try a simple query
        await db.execute_query("SELECT 1", ())
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Get cache stats
    cache_stats = {
        "total_entries": 0,
        "total_size_mb": 0.0
    }
    try:
        cache = CacheManager()
        # CacheManager doesn't expose stats directly, so we estimate
        # In a real implementation, you'd track this in CacheManager
        cache_stats["status"] = "operational"
    except Exception as e:
        cache_stats["status"] = f"error: {str(e)}"
    
    # AI service availability (placeholder for now - no actual AI service yet)
    ai_service = "not_configured"  # Will be "available" when LLM is integrated
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "version": "0.1.0",
        "database": db_status,
        "cache_stats": cache_stats,
        "ai_service": ai_service
    }
