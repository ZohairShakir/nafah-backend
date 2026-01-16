"""Seasonal product detection analytics."""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
from storage.database import Database
from storage.cache import CacheManager
from utils.logging import setup_logging

logger = setup_logging()


async def compute_seasonality(
    db: Database,
    cache: CacheManager,
    dataset_id: str,
    min_seasonality_score: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Detect seasonal products using statistical analysis.
    
    Args:
        db: Database instance
        cache: Cache manager instance
        dataset_id: Dataset identifier
        min_seasonality_score: Minimum seasonality score (0-1)
        
    Returns:
        List of seasonal products with peak months
    """
    # Check cache
    cache_key = f"seasonality_{min_seasonality_score}"
    cached = cache.read(dataset_id, cache_key)
    if cached is not None:
        logger.info(f"Returning cached seasonality for dataset {dataset_id}")
        return cached.to_dict('records')
    
    # Load sales data
    query = """
        SELECT 
            product_id,
            product_name,
            date,
            quantity
        FROM raw_sales
        WHERE dataset_id = ?
    """
    rows = await db.execute_query(query, (dataset_id,))
    
    if not rows:
        return []
    
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.month
    
    results = []
    
    # Analyze each product
    for product_id in df['product_id'].unique():
        product_data = df[df['product_id'] == product_id].copy()
        product_name = product_data['product_name'].iloc[0]
        
        # Group by month
        monthly_sales = product_data.groupby('month')['quantity'].sum()
        
        # Need at least 6 months of data
        if len(monthly_sales) < 6:
            continue
        
        # Calculate coefficient of variation (CV) as seasonality indicator
        mean_sales = monthly_sales.mean()
        std_sales = monthly_sales.std()
        
        if mean_sales == 0:
            continue
        
        cv = std_sales / mean_sales
        
        # Normalize to 0-1 score
        # CV > 0.5 indicates high variability (seasonal)
        seasonality_score = min(cv / 0.5, 1.0)
        
        if seasonality_score < min_seasonality_score:
            continue
        
        # Identify peak months (top 2-3 months)
        peak_months = monthly_sales.nlargest(3).index.tolist()
        low_months = monthly_sales.nsmallest(3).index.tolist()
        
        results.append({
            'product_name': product_name,
            'product_id': product_id,
            'seasonality_score': round(seasonality_score, 3),
            'peak_months': sorted(peak_months),
            'low_months': sorted(low_months),
            'category': product_data['category'].iloc[0] if 'category' in product_data.columns else None
        })
    
    # Sort by seasonality score
    results = sorted(results, key=lambda x: x['seasonality_score'], reverse=True)
    
    # Cache results
    result_df = pd.DataFrame(results)
    if not result_df.empty:
        cache.write(dataset_id, cache_key, result_df)
    
    logger.info(f"Computed seasonality for dataset {dataset_id}: {len(results)} products")
    
    return results
