"""Growth opportunity rules."""

from typing import List, Dict, Any


def evaluate_seasonal_peak_rule(seasonal_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluate seasonal peak opportunity rule.
    
    Args:
        seasonal_data: List of seasonal products from analytics
        
    Returns:
        List of insights
    """
    insights = []
    
    # Get current month (1-12)
    from datetime import datetime
    current_month = datetime.now().month
    
    for item in seasonal_data:
        peak_months = item.get('peak_months', [])
        seasonality_score = item.get('seasonality_score', 0)
        
        # Check if approaching peak season (within 1-2 months)
        months_until_peak = None
        for peak_month in peak_months:
            if peak_month >= current_month:
                months_until_peak = peak_month - current_month
                break
        
        if months_until_peak is not None and months_until_peak <= 2:
            insights.append({
                'insight_id': f"seasonal_peak_{item.get('product_id', 'unknown')}",
                'title': f"Seasonal Peak Approaching: {item.get('product_name', 'Unknown')}",
                'category': 'growth',
                'confidence': 'high' if seasonality_score > 0.7 else 'medium',
                'supporting_metrics': {
                    'seasonality_score': seasonality_score,
                    'peak_months': peak_months,
                    'months_until_peak': months_until_peak
                },
                'recommended_action': (
                    f"Prepare inventory for {item.get('product_name')} as peak season "
                    f"approaches in {months_until_peak} month(s)"
                ),
                'match_strength': seasonality_score,
                'significance': 0.8 if months_until_peak == 1 else 0.6
            })
    
    return insights


def evaluate_high_velocity_low_stock_rule(
    best_sellers: List[Dict[str, Any]],
    inventory_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Evaluate high-velocity low-stock opportunity.
    
    Args:
        best_sellers: Top selling products
        inventory_data: Current inventory levels
        
    Returns:
        List of insights
    """
    insights = []
    
    # Create inventory lookup
    inventory_lookup = {item['product_id']: item for item in inventory_data}
    
    for product in best_sellers[:10]:  # Top 10 sellers
        product_id = product.get('product_id')
        if product_id in inventory_lookup:
            stock = inventory_lookup[product_id].get('current_stock', 0)
            quantity_sold = product.get('total_quantity', 0)
            
            # Low stock relative to sales velocity
            if stock < quantity_sold * 0.1:  # Less than 10% of monthly sales
                insights.append({
                    'insight_id': f"restock_opportunity_{product_id}",
                    'title': f"Restock Opportunity: {product.get('product_name', 'Unknown')}",
                    'category': 'growth',
                    'confidence': 'high',
                    'supporting_metrics': {
                        'current_stock': stock,
                        'monthly_sales': quantity_sold,
                        'revenue': product.get('total_amount', 0)
                    },
                    'recommended_action': (
                        f"Restock {product.get('product_name')} immediately. "
                        f"Current stock: {stock}, Monthly sales: {quantity_sold:.0f}"
                    ),
                    'match_strength': 0.9,
                    'significance': min(quantity_sold / 100, 1.0)
                })
    
    return insights
