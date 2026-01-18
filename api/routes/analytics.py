"""Analytics endpoints."""

import os
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from storage.database import Database
from storage.cache import CacheManager
from services.analytics import (
    best_sellers,
    revenue,
    seasonality,
    inventory,
    dead_stock,
    profitability,
    trends
)
from services.analytics import daily_sales
from services.ml import predictions

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

DB_PATH = os.getenv("DATABASE_PATH", "data/nafah.db")


@router.get("/{dataset_id}/best-sellers")
async def get_best_sellers(
    dataset_id: str,
    limit: int = Query(10, ge=1, le=100),
    period: Optional[str] = Query(None, description="Period filter (YYYY-MM)"),
    sort_by: str = Query("quantity", description="Sort by 'quantity' or 'revenue'")
):
    """Get best selling products."""
    db = Database(DB_PATH)
    cache = CacheManager()
    
    try:
        results = await best_sellers.compute_best_sellers(
            db, cache, dataset_id, limit, period, sort_by
        )
        return {
            "dataset_id": dataset_id,
            "analytics_type": "best_sellers",
            "period": period,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/revenue-contribution")
async def get_revenue_contribution(
    dataset_id: str,
    limit: int = Query(20, ge=1, le=100)
):
    """Get revenue contribution by product."""
    db = Database(DB_PATH)
    cache = CacheManager()
    
    try:
        result = await revenue.compute_revenue_contribution(
            db, cache, dataset_id, limit
        )
        return {
            "dataset_id": dataset_id,
            "analytics_type": "revenue_contribution",
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/seasonality")
async def get_seasonality(
    dataset_id: str,
    min_seasonality_score: float = Query(0.3, ge=0.0, le=1.0)
):
    """Get seasonal products."""
    db = Database(DB_PATH)
    cache = CacheManager()
    
    try:
        results = await seasonality.compute_seasonality(
            db, cache, dataset_id, min_seasonality_score
        )
        return {
            "dataset_id": dataset_id,
            "analytics_type": "seasonality",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/inventory-velocity")
async def get_inventory_velocity(dataset_id: str):
    """Get inventory velocity (turnover rates)."""
    db = Database(DB_PATH)
    cache = CacheManager()
    
    try:
        results = await inventory.compute_inventory_velocity(
            db, cache, dataset_id
        )
        return {
            "dataset_id": dataset_id,
            "analytics_type": "inventory_velocity",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/dead-stock")
async def get_dead_stock(
    dataset_id: str,
    days_threshold: int = Query(90, ge=1)
):
    """Get dead stock items."""
    db = Database(DB_PATH)
    cache = CacheManager()
    
    try:
        results = await dead_stock.compute_dead_stock(
            db, cache, dataset_id, days_threshold
        )
        return {
            "dataset_id": dataset_id,
            "analytics_type": "dead_stock",
            "threshold_days": days_threshold,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/profitability")
async def get_profitability(dataset_id: str):
    """Get profitability ranking."""
    db = Database(DB_PATH)
    cache = CacheManager()
    
    try:
        results = await profitability.compute_profitability(
            db, cache, dataset_id
        )
        return {
            "dataset_id": dataset_id,
            "analytics_type": "profitability",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/trends")
async def get_trends(
    dataset_id: str,
    metric: str = Query("revenue", description="Metric: revenue, quantity, or profit"),
    months: int = Query(6, ge=1, le=24)
):
    """Get month-over-month trends."""
    db = Database(DB_PATH)
    cache = CacheManager()
    
    try:
        results = await trends.compute_trends(
            db, cache, dataset_id, metric, months
        )
        return {
            "dataset_id": dataset_id,
            "analytics_type": "trends",
            "metric": metric,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/daily-sales")
async def get_daily_sales(
    dataset_id: str,
    year: int = Query(..., ge=2000, le=2100, description="Year (e.g., 2024)"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)")
):
    """Get daily sales for a specific month."""
    db = Database(DB_PATH)
    cache = CacheManager()
    
    try:
        results = await daily_sales.compute_daily_sales(
            db, cache, dataset_id, year, month
        )
        return {
            "dataset_id": dataset_id,
            "analytics_type": "daily_sales",
            "year": year,
            "month": month,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/ml/sales-forecast")
async def get_sales_forecast(
    dataset_id: str,
    days_ahead: int = Query(7, ge=1, le=30, description="Days to forecast ahead"),
    product_id: Optional[str] = Query(None, description="Optional product ID for specific forecast")
):
    """Get ML-based sales forecast for next N days."""
    db = Database(DB_PATH)
    cache = CacheManager()
    
    try:
        result = await predictions.predict_sales_forecast(
            db, cache, dataset_id, days_ahead, product_id
        )
        return {
            "dataset_id": dataset_id,
            "analytics_type": "ml_sales_forecast",
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/ml/anomalies")
async def get_anomalies(
    dataset_id: str,
    threshold: float = Query(2.0, ge=1.0, le=5.0, description="Z-score threshold for anomaly detection")
):
    """Detect anomalies in sales data using ML."""
    db = Database(DB_PATH)
    cache = CacheManager()
    
    try:
        results = await predictions.detect_anomalies(db, cache, dataset_id, threshold)
        return {
            "dataset_id": dataset_id,
            "analytics_type": "ml_anomalies",
            "threshold": threshold,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{dataset_id}/ml/demand-prediction/{product_id}")
async def get_demand_prediction(
    dataset_id: str,
    product_id: str,
    days_ahead: int = Query(30, ge=7, le=90, description="Days to predict ahead")
):
    """Predict demand for a specific product with recommended stock level."""
    db = Database(DB_PATH)
    cache = CacheManager()
    
    try:
        result = await predictions.predict_demand(db, cache, dataset_id, product_id, days_ahead)
        return {
            "dataset_id": dataset_id,
            "analytics_type": "ml_demand_prediction",
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
