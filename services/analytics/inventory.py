"""Inventory velocity analytics."""

import pandas as pd
from typing import List, Dict, Any
from storage.database import Database
from storage.cache import CacheManager
from utils.logging import setup_logging

logger = setup_logging()


async def compute_inventory_velocity(
    db: Database,
    cache: CacheManager,
    dataset_id: str
) -> List[Dict[str, Any]]:
    """
    Compute inventory velocity (turnover rate).
    
    Args:
        db: Database instance
        cache: Cache manager instance
        dataset_id: Dataset identifier
        
    Returns:
        List of products with velocity scores
    """
    # Check cache
    cache_key = "inventory_velocity"
    cached = cache.read(dataset_id, cache_key)
    if cached is not None:
        logger.info(f"Returning cached inventory velocity for dataset {dataset_id}")
        return cached.to_dict('records')
    
    # Get sales data (aggregated by product)
    sales_query = """
        SELECT 
            product_id,
            product_name,
            SUM(quantity) as total_quantity_sold
        FROM raw_sales
        WHERE dataset_id = ?
        GROUP BY product_id, product_name
    """
    sales_rows = await db.execute_query(sales_query, (dataset_id,))
    
    # Create DataFrame from sales only
    if not sales_rows:
        return []

    sales_df = pd.DataFrame(sales_rows)

    # Approximate turnover rate based purely on sales volume
    # Higher quantity sold -> higher turnover
    max_qty = sales_df['total_quantity_sold'].max() or 1
    sales_df['turnover_rate'] = sales_df['total_quantity_sold'] / max_qty * 12  # scale to 0–12

    # Approximate average days in stock inversely from turnover
    sales_df['avg_days_in_stock'] = sales_df['turnover_rate'].apply(
        lambda tr: 365 / tr if tr > 0 else 999
    )
    
    # Categorize velocity
    def categorize_velocity(turnover_rate):
        if turnover_rate >= 12:  # 12+ times per year
            return "high"
        elif turnover_rate >= 6:  # 6-12 times per year
            return "medium"
        else:
            return "low"
    
    sales_df['velocity_score'] = sales_df['turnover_rate'].apply(categorize_velocity)
    
    # Sort by turnover rate
    sales_df = sales_df.sort_values('turnover_rate', ascending=False)
    
    # Convert to dict
    results = sales_df[[
        'product_name', 'product_id', 'velocity_score',
        'turnover_rate', 'avg_days_in_stock'
    ]].to_dict('records')
    
    # Cache results
    cache.write(dataset_id, cache_key, sales_df)
    
    logger.info(f"Computed inventory velocity for dataset {dataset_id}: {len(results)} products")
    
    return results
