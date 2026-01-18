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
    
    # Get sales data (aggregated by product) with date info
    sales_query = """
        SELECT 
            product_id,
            product_name,
            SUM(quantity) as total_quantity_sold,
            SUM(total_amount) as total_revenue,
            COUNT(DISTINCT date) as days_with_sales,
            MAX(date) as last_sale_date,
            MIN(date) as first_sale_date
        FROM raw_sales
        WHERE dataset_id = ?
        GROUP BY product_id, product_name
    """
    sales_rows = await db.execute_query(sales_query, (dataset_id,))
    
    # Get inventory data if available (only columns that exist in schema)
    inventory_query = """
        SELECT 
            product_id,
            current_stock,
            unit_cost,
            category
        FROM raw_inventory
        WHERE dataset_id = ?
    """
    inventory_rows = await db.execute_query(inventory_query, (dataset_id,))
    
    # Create DataFrame from sales
    if not sales_rows:
        return []

    sales_df = pd.DataFrame(sales_rows)
    inventory_df = pd.DataFrame(inventory_rows) if inventory_rows else pd.DataFrame()
    
    # Merge with inventory (only columns that exist)
    if not inventory_df.empty:
        sales_df = sales_df.merge(
            inventory_df[['product_id', 'current_stock', 'unit_cost', 'category']],
            on='product_id',
            how='left',
            suffixes=('', '_inv')
        )
        sales_df['current_stock'] = sales_df['current_stock'].fillna(0)
        sales_df['unit_cost'] = sales_df['unit_cost'].fillna(0)
        # Use inventory category if available, otherwise keep sales category
        if 'category_inv' in sales_df.columns:
            sales_df['category'] = sales_df['category_inv'].fillna(sales_df.get('category', ''))
            sales_df = sales_df.drop(columns=['category_inv'], errors='ignore')
    else:
        sales_df['current_stock'] = 0
        sales_df['unit_cost'] = 0
    
    # Calculate days since first sale (for velocity calculation)
    sales_df['first_sale_date'] = pd.to_datetime(sales_df['first_sale_date'])
    sales_df['last_sale_date'] = pd.to_datetime(sales_df['last_sale_date'])
    today = pd.Timestamp.now()
    sales_df['days_active'] = (today - sales_df['first_sale_date']).dt.days.clip(lower=1)
    sales_df['days_since_last_sale'] = (today - sales_df['last_sale_date']).dt.days
    
    # Calculate daily average sales
    sales_df['avg_daily_sales'] = sales_df['total_quantity_sold'] / sales_df['days_active']
    
    # Calculate turnover rate (annualized)
    sales_df['turnover_rate'] = (sales_df['total_quantity_sold'] / sales_df['days_active']) * 365
    
    # Calculate days of stock remaining (if we have stock data)
    sales_df['days_of_stock'] = sales_df.apply(
        lambda row: row['current_stock'] / row['avg_daily_sales'] if row['avg_daily_sales'] > 0 else 999,
        axis=1
    )
    
    # Calculate reorder urgency score (0-100)
    # Factors: low stock, high velocity, days since last sale
    def calculate_reorder_score(row):
        score = 0
        
        # High velocity products get priority
        if row['avg_daily_sales'] > 0:
            if row['avg_daily_sales'] > 10:
                score += 40  # Very fast moving
            elif row['avg_daily_sales'] > 5:
                score += 30
            elif row['avg_daily_sales'] > 2:
                score += 20
            else:
                score += 10
        
        # Low stock urgency
        if row['current_stock'] > 0:
            if row['days_of_stock'] < 7:
                score += 40  # Critical
            elif row['days_of_stock'] < 14:
                score += 30  # Urgent
            elif row['days_of_stock'] < 30:
                score += 20  # Moderate
            else:
                score += 5
        else:
            # No stock but has sales = urgent
            if row['total_quantity_sold'] > 0:
                score += 50
        
        # Recent sales activity
        if row['days_since_last_sale'] < 7:
            score += 20
        elif row['days_since_last_sale'] < 30:
            score += 10
        
        return min(100, score)
    
    sales_df['reorder_score'] = sales_df.apply(calculate_reorder_score, axis=1)
    
    # Approximate average days in stock inversely from turnover
    sales_df['avg_days_in_stock'] = sales_df['turnover_rate'].apply(
        lambda tr: 365 / tr if tr > 0 else 999
    )
    
    # Categorize velocity
    def categorize_velocity(turnover_rate, avg_daily_sales):
        if turnover_rate >= 12 or avg_daily_sales > 10:  # 12+ times per year or >10 units/day
            return "high"
        elif turnover_rate >= 6 or avg_daily_sales > 3:  # 6-12 times per year or >3 units/day
            return "medium"
        else:
            return "low"
    
    sales_df['velocity_score'] = sales_df.apply(
        lambda row: categorize_velocity(row['turnover_rate'], row['avg_daily_sales']),
        axis=1
    )
    
    # Sort by reorder score (most urgent first), then by turnover
    sales_df = sales_df.sort_values(['reorder_score', 'turnover_rate'], ascending=[False, False])
    
    # Convert to dict
    results = sales_df[[
        'product_name', 'product_id', 'velocity_score',
        'turnover_rate', 'avg_days_in_stock', 'current_stock',
        'avg_daily_sales', 'days_of_stock', 'reorder_score',
        'days_since_last_sale'
    ]].to_dict('records')
    
    # Cache results
    cache.write(dataset_id, cache_key, sales_df)
    
    logger.info(f"Computed inventory velocity for dataset {dataset_id}: {len(results)} products")
    
    return results
