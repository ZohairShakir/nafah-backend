"""Efficiency optimization rules."""

from typing import List, Dict, Any


def evaluate_low_margin_rule(profitability_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Evaluate low profit margin rule.
    
    Args:
        profitability_data: Profitability rankings
        
    Returns:
        List of insights
    """
    insights = []
    
    for item in profitability_data:
        profit_margin = item.get('profit_margin', 0)
        revenue = item.get('revenue', 0)
        
        # Low margin but high volume
        if profit_margin < 10 and revenue > 10000:
            insights.append({
                'insight_id': f"low_margin_{item.get('product_id', 'unknown')}",
                'title': f"Low Margin Product: {item.get('product_name', 'Unknown')}",
                'category': 'efficiency',
                'confidence': 'medium',
                'supporting_metrics': {
                    'profit_margin': profit_margin,
                    'revenue': revenue,
                    'profit': item.get('profit', 0)
                },
                'recommended_action': (
                    f"Review pricing strategy for {item.get('product_name')}. "
                    f"Current margin: {profit_margin:.1f}%"
                ),
                'match_strength': 0.7,
                'significance': min(revenue / 50000, 1.0)
            })
    
    return insights
