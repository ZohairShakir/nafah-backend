"""Profitability ranking analytics."""

import pandas as pd
from typing import List, Dict, Any
from storage.database import Database
from storage.cache import CacheManager
from utils.logging import setup_logging

logger = setup_logging()


async def compute_profitability(
    db: Database,
    cache: CacheManager,
    dataset_id: str
) -> List[Dict[str, Any]]:
    """
    Compute profitability ranking by product.
    
    Args:
        db: Database instance
        cache: Cache manager instance
        dataset_id: Dataset identifier
        
    Returns:
        List of products ranked by profitability
    """
    # Check cache
    cache_key = "profitability"
    cached = cache.read(dataset_id, cache_key)
    if cached is not None:
        logger.info(f"Returning cached profitability for dataset {dataset_id}")
        return cached.to_dict('records')
    
    # Get sales data
    sales_query = """
        SELECT 
            product_id,
            product_name,
            SUM(total_amount) as revenue,
            SUM(quantity) as total_quantity
        FROM raw_sales
        WHERE dataset_id = ?
        GROUP BY product_id, product_name
    """
    sales_rows = await db.execute_query(sales_query, (dataset_id,))
    
    # Get inventory/cost data
    inventory_query = """
        SELECT 
            product_id,
            unit_cost,
            category
        FROM raw_inventory
        WHERE dataset_id = ?
    """
    inventory_rows = await db.execute_query(inventory_query, (dataset_id,))
    
    if not sales_rows:
        return []
    
    # Create DataFrames
    sales_df = pd.DataFrame(sales_rows)
    inventory_df = pd.DataFrame(inventory_rows) if inventory_rows else pd.DataFrame()
    
    # Merge with inventory for cost data
    if not inventory_df.empty:
        merged = sales_df.merge(
            inventory_df[['product_id', 'unit_cost', 'category']],
            on='product_id',
            how='left'
        )
    else:
        merged = sales_df.copy()
        merged['unit_cost'] = 0
        merged['category'] = None
    
    # Calculate cost (quantity * unit_cost)
    merged['cost'] = merged['total_quantity'] * merged['unit_cost'].fillna(0)
    
    # Calculate profit
    merged['profit'] = merged['revenue'] - merged['cost']
    
    # Calculate profit margin
    merged['profit_margin'] = merged.apply(
        lambda row: (row['profit'] / row['revenue'] * 100) if row['revenue'] > 0 else 0,
        axis=1
    )
    
    # Sort by profit margin
    merged = merged.sort_values('profit_margin', ascending=False)
    
    # Add rank
    merged['rank'] = range(1, len(merged) + 1)
    
    # Convert to dict
    results = merged[[
        'product_name', 'product_id', 'revenue', 'cost',
        'profit', 'profit_margin', 'rank', 'category'
    ]].to_dict('records')
    
    # Cache results
    cache.write(dataset_id, cache_key, merged)
    
    logger.info(f"Computed profitability for dataset {dataset_id}: {len(results)} products")
    
    return results
