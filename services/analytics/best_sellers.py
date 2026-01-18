"""Best selling products analytics."""

import pandas as pd
from typing import List, Dict, Any, Optional
from storage.database import Database
from storage.cache import CacheManager
from utils.logging import setup_logging

logger = setup_logging()


async def compute_best_sellers(
    db: Database,
    cache: CacheManager,
    dataset_id: str,
    limit: int = 10,
    period: Optional[str] = None,
    sort_by: str = "quantity"
) -> List[Dict[str, Any]]:
    """
    Compute best selling products.
    
    Args:
        db: Database instance
        cache: Cache manager instance
        dataset_id: Dataset identifier
        limit: Maximum number of results
        period: Optional period filter (YYYY-MM format)
        sort_by: Sort by 'quantity' or 'revenue'
        
    Returns:
        List of best selling products with rankings
    """
    # Check cache
    cache_key = f"best_sellers_{sort_by}_{limit}"
    if period:
        cache_key += f"_{period}"
    
    cached = cache.read(dataset_id, cache_key)
    if cached is not None:
        logger.info(f"Returning cached best sellers for dataset {dataset_id}")
        return cached.to_dict('records')
    
    # Load sales data
    query = """
        SELECT 
            product_name,
            product_id,
            quantity,
            total_amount,
            category
        FROM raw_sales
        WHERE dataset_id = ?
    """
    params = [dataset_id]
    
    if period:
        # Filter by period (YYYY-MM)
        query += " AND strftime('%Y-%m', date) = ?"
        params.append(period)
    
    rows = await db.execute_query(query, tuple(params))
    
    if not rows:
        logger.warning(f"No sales data found for dataset {dataset_id}")
        return []
    
    df = pd.DataFrame(rows)
    
    # Aggregate by product
    aggregated = df.groupby(['product_name', 'product_id', 'category']).agg({
        'quantity': 'sum',
        'total_amount': 'sum'
    }).reset_index()
    
    # Sort by specified column
    sort_column = 'quantity' if sort_by == 'quantity' else 'total_amount'
    aggregated = aggregated.sort_values(sort_column, ascending=False)
    
    # Add rank
    aggregated['rank'] = range(1, len(aggregated) + 1)
    
    # Select top N
    result_df = aggregated.head(limit)
    
    # Convert to dict and normalize field names for frontend
    results = []
    for _, row in result_df.iterrows():
        results.append({
            'product_name': row['product_name'],
            'product_id': row.get('product_id'),
            'total_quantity': float(row['quantity']),  # Map quantity -> total_quantity for frontend
            'quantity': float(row['quantity']),  # Keep both for backward compatibility
            'total_amount': float(row['total_amount']),
            'total_revenue': float(row['total_amount']),  # Map total_amount -> total_revenue
            'category': row.get('category'),
            'rank': int(row['rank'])
        })
    
    # Cache results
    cache.write(dataset_id, cache_key, result_df)
    
    logger.info(f"Computed best sellers for dataset {dataset_id}: {len(results)} products")
    
    return results
