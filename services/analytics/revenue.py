"""Revenue contribution analytics."""

import pandas as pd
from typing import List, Dict, Any
from storage.database import Database
from storage.cache import CacheManager
from utils.logging import setup_logging

logger = setup_logging()


async def compute_revenue_contribution(
    db: Database,
    cache: CacheManager,
    dataset_id: str,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Compute revenue contribution by product.
    
    Args:
        db: Database instance
        cache: Cache manager instance
        dataset_id: Dataset identifier
        limit: Maximum number of results
        
    Returns:
        Dictionary with total revenue and product contributions
    """
    # Check cache
    cache_key = f"revenue_contribution_{limit}"
    cached = cache.read(dataset_id, cache_key)
    if cached is not None:
        logger.info(f"Returning cached revenue contribution for dataset {dataset_id}")
        # Reconstruct dict from cached DataFrame
        results = cached.to_dict('records')
        total_revenue = cached['revenue'].sum()
        return {
            "total_revenue": float(total_revenue),
            "results": results
        }
    
    # Load sales data
    query = """
        SELECT 
            product_name,
            product_id,
            total_amount,
            category
        FROM raw_sales
        WHERE dataset_id = ?
    """
    rows = await db.execute_query(query, (dataset_id,))
    
    if not rows:
        return {
            "total_revenue": 0.0,
            "results": []
        }
    
    df = pd.DataFrame(rows)
    
    # Calculate total revenue
    total_revenue = df['total_amount'].sum()
    
    if total_revenue == 0:
        return {
            "total_revenue": 0.0,
            "results": []
        }
    
    # Aggregate by product
    aggregated = df.groupby(['product_name', 'product_id', 'category']).agg({
        'total_amount': 'sum'
    }).reset_index()
    
    # Calculate percentage contribution
    aggregated['revenue'] = aggregated['total_amount']
    aggregated['percentage'] = (aggregated['revenue'] / total_revenue * 100).round(2)
    
    # Sort by revenue
    aggregated = aggregated.sort_values('revenue', ascending=False)
    
    # Add rank
    aggregated['rank'] = range(1, len(aggregated) + 1)
    
    # Select top N
    result_df = aggregated.head(limit)
    
    # Convert to dict
    results = result_df[['product_name', 'product_id', 'revenue', 'percentage', 'rank', 'category']].to_dict('records')
    
    # Cache results
    cache.write(dataset_id, cache_key, result_df)
    
    logger.info(f"Computed revenue contribution for dataset {dataset_id}")
    
    return {
        "total_revenue": float(total_revenue),
        "results": results
    }
