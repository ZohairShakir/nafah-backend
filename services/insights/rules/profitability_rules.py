"""Profitability optimization rules."""

from typing import List, Dict, Any


def evaluate_high_profit_opportunity(profitability_data: List[Dict[str, Any]], best_sellers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Identify high-profit products that could be promoted more.
    
    Args:
        profitability_data: Profitability rankings
        best_sellers: Top selling products
        
    Returns:
        List of insights
    """
    insights = []
    
    # Get top sellers IDs
    top_seller_ids = {p.get('product_id') for p in best_sellers[:10]}
    
    for item in profitability_data:
        profit_margin = item.get('profit_margin', 0)
        revenue = item.get('revenue', 0)
        product_id = item.get('product_id')
        
        # High margin products not in top sellers
        if profit_margin > 20 and revenue > 5000 and product_id not in top_seller_ids:
            insights.append({
                'insight_id': f"high_profit_opportunity_{product_id}",
                'title': f"Promote High-Margin Product: {item.get('product_name', 'Unknown')}",
                'category': 'growth',
                'confidence': 'medium',
                'supporting_metrics': {
                    'profit_margin': profit_margin,
                    'revenue': revenue,
                    'profit': item.get('profit', 0)
                },
                'recommended_action': (
                    f"{item.get('product_name')} has {profit_margin:.1f}% profit margin but isn't in top sellers. "
                    f"Consider promoting it more to increase overall profitability."
                ),
                'match_strength': min(profit_margin / 50, 1.0),
                'significance': min(revenue / 30000, 1.0)
            })
    
    return insights


def evaluate_profit_concentration(best_sellers: List[Dict[str, Any]], profitability_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Check if business is too dependent on low-margin products.
    
    Args:
        best_sellers: Top selling products
        profitability_data: Profitability rankings
        
    Returns:
        List of insights
    """
    insights = []
    
    # Create profitability lookup
    profit_lookup = {item.get('product_id'): item for item in profitability_data}
    
    # Check top 5 sellers
    top_5_revenue = 0
    low_margin_count = 0
    total_profit = 0
    
    for product in best_sellers[:5]:
        product_id = product.get('product_id')
        revenue = product.get('total_amount', 0) or product.get('total_revenue', 0)
        top_5_revenue += revenue
        
        if product_id in profit_lookup:
            margin = profit_lookup[product_id].get('profit_margin', 0)
            profit = profit_lookup[product_id].get('profit', 0) or (revenue * margin / 100)
            total_profit += profit
            
            if margin < 10:
                low_margin_count += 1
    
    # If most top sellers have low margins
    if low_margin_count >= 3 and top_5_revenue > 50000:
        avg_margin = (total_profit / top_5_revenue * 100) if top_5_revenue > 0 else 0
        insights.append({
            'insight_id': 'profit_concentration_risk',
            'title': 'Diversify Product Mix',
            'category': 'efficiency',
            'confidence': 'high',
            'supporting_metrics': {
                'low_margin_top_sellers': low_margin_count,
                'top_5_revenue': top_5_revenue,
                'average_margin': avg_margin
            },
            'recommended_action': (
                f"Your top 5 products generate ₹{top_5_revenue:,.0f} but {low_margin_count} have margins below 10%. "
                f"Average margin: {avg_margin:.1f}%. Consider focusing on higher-margin products to improve profitability."
            ),
            'match_strength': min(low_margin_count / 5, 1.0),
            'significance': min(top_5_revenue / 100000, 1.0)
        })
    
    return insights
