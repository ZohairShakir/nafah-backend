"""Dead stock detection analytics."""

import pandas as pd
from typing import List, Dict, Any
from storage.database import Database
from storage.cache import CacheManager
from datetime import datetime, timedelta
from utils.logging import setup_logging

logger = setup_logging()


async def compute_dead_stock(
    db: Database,
    cache: CacheManager,
    dataset_id: str,
    days_threshold: int = 90
) -> List[Dict[str, Any]]:
    """
    Detect dead stock (products with no sales for threshold days).
    
    Args:
        db: Database instance
        cache: Cache manager instance
        dataset_id: Dataset identifier
        days_threshold: Days since last sale threshold
        
    Returns:
        List of dead stock items
    """
    # Check cache
    cache_key = f"dead_stock_{days_threshold}"
    cached = cache.read(dataset_id, cache_key)
    if cached is not None:
        logger.info(f"Returning cached dead stock for dataset {dataset_id}")
        return cached.to_dict('records')
    
    # Get latest sale date per product
    query = """
        SELECT 
            product_id,
            product_name,
            MAX(date) as last_sale_date
        FROM raw_sales
        WHERE dataset_id = ?
        GROUP BY product_id, product_name
    """
    sales_rows = await db.execute_query(query, (dataset_id,))
    
    if not sales_rows:
        return []
    
    # Get current inventory
    inventory_query = """
        SELECT 
            product_id,
            product_name,
            current_stock,
            unit_cost,
            category
        FROM raw_inventory
        WHERE dataset_id = ?
    """
    inventory_rows = await db.execute_query(inventory_query, (dataset_id,))
    
    # Create DataFrames
    sales_df = pd.DataFrame(sales_rows)
    sales_df['last_sale_date'] = pd.to_datetime(sales_df['last_sale_date'])
    
    inventory_df = pd.DataFrame(inventory_rows) if inventory_rows else pd.DataFrame()
    
    # Calculate days since last sale
    today = pd.Timestamp.now()
    sales_df['days_since_sale'] = (today - sales_df['last_sale_date']).dt.days
    
    # Filter by threshold
    dead_stock = sales_df[sales_df['days_since_sale'] > days_threshold].copy()
    
    # Merge with inventory if available
    if not inventory_df.empty:
        dead_stock = dead_stock.merge(
            inventory_df[['product_id', 'current_stock', 'unit_cost', 'category']],
            on='product_id',
            how='left'
        )
        # Fill missing values
        dead_stock['current_stock'] = dead_stock['current_stock'].fillna(0)
        dead_stock['unit_cost'] = dead_stock['unit_cost'].fillna(0)
    else:
        dead_stock['current_stock'] = 0
        dead_stock['unit_cost'] = 0
        dead_stock['category'] = None
    
    # Calculate estimated value
    dead_stock['estimated_value'] = (
        dead_stock['current_stock'] * dead_stock['unit_cost']
    )
    
    # If inventory is not available, still report products with no recent sales
    # even if we don't know exact stock; estimated_value will be 0 in that case.
    
    # Sort by days since sale (most critical first)
    dead_stock = dead_stock.sort_values('days_since_sale', ascending=False)
    
    # Convert to dict
    results = dead_stock[[
        'product_name', 'product_id', 'days_since_sale',
        'current_stock', 'unit_cost', 'estimated_value', 'category'
    ]].to_dict('records')
    
    # Cache results
    cache.write(dataset_id, cache_key, dead_stock)
    
    logger.info(f"Computed dead stock for dataset {dataset_id}: {len(results)} items")
    
    return results
