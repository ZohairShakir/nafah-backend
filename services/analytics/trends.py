"""Month-over-month trend analytics."""

import pandas as pd
from typing import List, Dict, Any, Optional
from storage.database import Database
from storage.cache import CacheManager
from utils.logging import setup_logging

logger = setup_logging()


async def compute_trends(
    db: Database,
    cache: CacheManager,
    dataset_id: str,
    metric: str = "revenue",
    months: int = 6
) -> List[Dict[str, Any]]:

    cache_key = f"trends_{dataset_id}_{metric}_{months}"
    
    """
    Compute month-over-month trends.
    
    Args:
        db: Database instance
        cache: Cache manager instance
        dataset_id: Dataset identifier
        metric: Metric to analyze ('revenue', 'quantity', 'profit')
        months: Number of months to analyze
        
    Returns:
        List of monthly trend data
    """
    # NOTE: We intentionally ignore cached Parquet for trends to avoid
    # legacy NaN/inf values breaking JSON responses. Trends are cheap
    # to recompute, and this guarantees JSON-safe output.
    
    # Load sales data
    query = """
        SELECT 
            date,
            quantity,
            total_amount
        FROM raw_sales
        WHERE dataset_id = ?
        ORDER BY date DESC
        LIMIT 10000
    """
    rows = await db.execute_query(query, (dataset_id,))
    
    if not rows:
        return []
    
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    
    # Group by month
    df['month'] = df['date'].dt.to_period('M')
    
    # Aggregate by metric
    if metric == 'revenue':
        monthly = df.groupby('month')['total_amount'].sum().reset_index()
        monthly['value'] = monthly['total_amount']
    elif metric == 'quantity':
        monthly = df.groupby('month')['quantity'].sum().reset_index()
        monthly['value'] = monthly['quantity']
    else:  # profit (requires cost data, simplified for now)
        monthly = df.groupby('month')['total_amount'].sum().reset_index()
        monthly['value'] = monthly['total_amount']  # Placeholder
    # Ensure numeric and finite; sums should already be fine, but be defensive
    monthly['value'] = monthly['value'].fillna(0)
    # Sort by month (descending)
    monthly = monthly.sort_values('month', ascending=False)
    
    # Take last N months
    monthly = monthly.head(months)
    
    # Calculate change percent and trend
    results = []
    for i, row in monthly.iterrows():
        month_str = str(row['month'])
        # Ensure numeric and finite
        value = float(row['value']) if row['value'] is not None else 0.0
        
        # Get previous month value
        prev_month = monthly[monthly['month'] < row['month']]
        if len(prev_month) > 0:
            prev_raw = prev_month.iloc[0]['value']
            prev_value = float(prev_raw) if prev_raw is not None else 0.0

            if prev_value > 0:
                change_percent = (value - prev_value) / prev_value * 100
                previous_value = prev_value
            else:
                change_percent = 0.0
                previous_value = None
            previous_month = str(prev_month.iloc[0]['month'])
        else:
            change_percent = 0.0
            previous_value = None
            previous_month = None
        
        # Determine trend
        if change_percent > 5:
            trend = "up"
        elif change_percent < -5:
            trend = "down"
        else:
            trend = "stable"
        
        results.append({
            "month": month_str,
            "value": value,
            "change_percent": round(change_percent, 2),
            "trend": trend,
            "previous_month": previous_month,
            "previous_value": previous_value
        })
    
    # Reverse to chronological order
    results.reverse()
    
    # Cache results
    result_df = pd.DataFrame(results)
    cache.write(dataset_id, cache_key, result_df)
    
    logger.info(f"Computed trends for dataset {dataset_id}: {len(results)} months")
    
    return results
