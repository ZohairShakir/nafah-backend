"""Daily sales analytics for a specific month."""

import pandas as pd
from typing import List, Dict, Any
from storage.database import Database
from storage.cache import CacheManager
from utils.logging import setup_logging

logger = setup_logging()


async def compute_daily_sales(
    db: Database,
    cache: CacheManager,
    dataset_id: str,
    year: int,
    month: int
) -> List[Dict[str, Any]]:
    """
    Compute daily sales for a specific month.
    
    Args:
        db: Database instance
        cache: Cache manager instance
        dataset_id: Dataset identifier
        year: Year (e.g., 2024)
        month: Month (1-12)
        
    Returns:
        List of daily sales data
    """
    cache_key = f"daily_sales_{dataset_id}_{year}_{month:02d}"
    cached = cache.read(dataset_id, cache_key)
    if cached is not None:
        logger.info(f"Returning cached daily sales for dataset {dataset_id}, {year}-{month:02d}")
        return cached.to_dict('records')
    
    # Build date range
    from datetime import datetime
    start_date = datetime(year, month, 1)
    # Get last day of month
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # Load sales data for the month
    query = """
        SELECT 
            date,
            SUM(total_amount) as daily_revenue,
            SUM(quantity) as daily_quantity
        FROM raw_sales
        WHERE dataset_id = ? 
            AND date >= ? 
            AND date < ?
        GROUP BY date
        ORDER BY date ASC
    """
    rows = await db.execute_query(query, (dataset_id, start_date, end_date))
    
    if not rows:
        return []
    
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    
    # Create complete daily series for the month
    days_in_month = (end_date - start_date).days
    date_range = pd.date_range(start=start_date, periods=days_in_month, freq='D')
    complete_df = pd.DataFrame({'date': date_range})
    
    # Merge with actual data
    df = complete_df.merge(df, on='date', how='left')
    df['daily_revenue'] = df['daily_revenue'].fillna(0)
    df['daily_quantity'] = df['daily_quantity'].fillna(0)
    
    # Extract day number
    df['day'] = df['date'].dt.day
    
    # Prepare results
    results = df[[
        'day', 'date', 'daily_revenue'
    ]].to_dict('records')
    
    # Convert date to string and rename for consistency
    for item in results:
        item['date'] = item['date'].strftime('%Y-%m-%d')
        item['value'] = float(item['daily_revenue'])
        del item['daily_revenue']
    
    # Cache results
    result_df = pd.DataFrame(results)
    cache.write(dataset_id, cache_key, result_df)
    
    logger.info(f"Computed daily sales for {year}-{month:02d}: {len(results)} days")
    
    return results
