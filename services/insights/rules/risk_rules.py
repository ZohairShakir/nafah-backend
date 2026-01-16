"""Risk identification rules."""

from typing import List, Dict, Any


def evaluate_dead_stock_rule(dead_stock_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluate dead stock risk rule.
    
    Args:
        dead_stock_data: List of dead stock items from analytics
        
    Returns:
        List of insights
    """
    insights = []
    
    for item in dead_stock_data:
        days_since_sale = item.get('days_since_sale', 0)
        current_stock = item.get('current_stock', 0)
        estimated_value = item.get('estimated_value', 0)
        
        if days_since_sale > 90 and current_stock > 0:
            # Higher confidence for older stock
            confidence = 'high' if days_since_sale > 180 else 'medium'
            
            insights.append({
                'insight_id': f"dead_stock_{item.get('product_id', 'unknown')}",
                'title': f"Dead Stock: {item.get('product_name', 'Unknown Product')}",
                'category': 'risk',
                'confidence': confidence,
                'supporting_metrics': {
                    'days_since_sale': days_since_sale,
                    'current_stock': current_stock,
                    'estimated_value': estimated_value
                },
                'recommended_action': (
                    f"Consider discounting or discontinuing {item.get('product_name')}. "
                    f"Stock value: ₹{estimated_value:.2f}"
                ),
                'match_strength': min(days_since_sale / 180, 1.0),
                'significance': min(estimated_value / 10000, 1.0) if estimated_value > 0 else 0
            })
    
    return insights
