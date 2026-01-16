"""Insights endpoints."""

import os
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from storage.database import Database
from storage.cache import CacheManager
from services.insights.engine import generate_insights, get_insights

router = APIRouter(prefix="/api/v1/insights", tags=["insights"])

DB_PATH = os.getenv("DATABASE_PATH", "data/nafah.db")


@router.get("/{dataset_id}")
async def list_insights(
    dataset_id: str,
    category: Optional[str] = Query(None, description="Filter by category"),
    confidence: Optional[str] = Query(None, description="Filter by confidence"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Get all insights for a dataset."""
    db = Database(DB_PATH)
    
    try:
        results = await get_insights(
            db, dataset_id, category, confidence, limit, offset
        )
        
        # Get total count
        conditions = ["dataset_id = ?", "is_active = 1"]
        params = [dataset_id]
        if category:
            conditions.append("category = ?")
            params.append(category)
        if confidence:
            conditions.append("confidence = ?")
            params.append(confidence)
        
        count_query = f"SELECT COUNT(*) as total FROM insights WHERE {' AND '.join(conditions)}"
        total_result = await db.execute_query(count_query, tuple(params), fetch_one=True)
        total = total_result['total'] if total_result else 0
        
        return {
            "dataset_id": dataset_id,
            "insights": results,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/{insight_id}")
async def get_insight(dataset_id: str, insight_id: str):
    """Get specific insight by ID."""
    db = Database(DB_PATH)
    
    try:
        query = """
            SELECT * FROM insights
            WHERE dataset_id = ? AND insight_id = ? AND is_active = 1
        """
        result = await db.execute_query(query, (dataset_id, insight_id), fetch_one=True)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Insight not found: {insight_id}"
            )
        
        # Parse JSON fields
        import json
        if 'supporting_metrics' in result and isinstance(result['supporting_metrics'], str):
            result['supporting_metrics'] = json.loads(result['supporting_metrics'])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{dataset_id}/generate")
async def generate_dataset_insights(dataset_id: str):
    """Force generate insights for a dataset."""
    db = Database(DB_PATH)
    cache = CacheManager()
    
    try:
        insights = await generate_insights(db, cache, dataset_id)
        return {
            "dataset_id": dataset_id,
            "insights_generated": len(insights),
            "insights": insights
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
