"""Calculate data quality metrics for insights."""

from typing import Dict, Any
from storage.database import Database


async def calculate_data_quality(
    db: Database,
    dataset_id: str
) -> Dict[str, Any]:
    """
    Calculate data quality metrics for a dataset.
    
    Args:
        db: Database instance
        dataset_id: Dataset identifier
        
    Returns:
        Dictionary with quality metrics
    """
    try:
        # Get dataset info
        dataset_query = "SELECT row_count, created_at FROM datasets WHERE dataset_id = ?"
        dataset = await db.execute_query(dataset_query, (dataset_id,), fetch_one=True)
        
        if not dataset:
            return {'completeness': 0.0, 'validity': 0.0, 'recency': 0.0}
        
        row_count = dataset.get('row_count', 0)
        
        # Check for missing/null values in raw_sales
        sales_query = """
            SELECT 
                COUNT(*) as total_rows,
                COUNT(DISTINCT product_name) as unique_products,
                COUNT(DISTINCT date) as unique_dates,
                SUM(CASE WHEN product_name IS NULL OR product_name = '' THEN 1 ELSE 0 END) as null_names,
                SUM(CASE WHEN total_amount IS NULL OR total_amount = 0 THEN 1 ELSE 0 END) as null_amounts,
                SUM(CASE WHEN quantity IS NULL OR quantity = 0 THEN 1 ELSE 0 END) as null_quantities
            FROM raw_sales
            WHERE dataset_id = ?
        """
        sales_stats = await db.execute_query(sales_query, (dataset_id,), fetch_one=True)
        
        if not sales_stats or sales_stats.get('total_rows', 0) == 0:
            return {'completeness': 0.0, 'validity': 0.0, 'recency': 0.0}
        
        total_rows = sales_stats['total_rows']
        null_names = sales_stats.get('null_names', 0)
        null_amounts = sales_stats.get('null_amounts', 0)
        null_quantities = sales_stats.get('null_quantities', 0)
        
        # Calculate completeness (percentage of non-null critical fields)
        total_fields = total_rows * 3  # product_name, total_amount, quantity
        missing_fields = null_names + null_amounts + null_quantities
        completeness = max(0.0, min(1.0, 1.0 - (missing_fields / total_fields)))
        
        # Calculate validity (data makes sense)
        # Check if we have diverse products and dates
        unique_products = sales_stats.get('unique_products', 0)
        unique_dates = sales_stats.get('unique_dates', 0)
        
        validity_score = 0.0
        if unique_products > 0:
            validity_score += 0.4  # Has multiple products
        if unique_dates > 1:
            validity_score += 0.4  # Has multiple dates
        if total_rows >= 10:
            validity_score += 0.2  # Has sufficient data points
        
        validity = min(1.0, validity_score)
        
        # Calculate recency (how fresh is the data)
        # For now, assume data is recent if dataset was created recently
        # In future, could check actual date ranges in the data
        recency = 1.0  # Default to recent
        
        # Combine into overall quality score
        overall_quality = (completeness * 0.5) + (validity * 0.3) + (recency * 0.2)
        
        return {
            'completeness': round(completeness, 2),
            'validity': round(validity, 2),
            'recency': round(recency, 2),
            'overall': round(overall_quality, 2),
            'total_rows': total_rows,
            'unique_products': unique_products,
            'unique_dates': unique_dates
        }
        
    except Exception as e:
        # If calculation fails, return conservative defaults
        return {'completeness': 0.5, 'validity': 0.5, 'recency': 1.0, 'overall': 0.6}
