"""Confidence scoring for insights."""

from typing import Dict, Any


def score_confidence(
    rule_result: Dict[str, Any],
    data_quality: Dict[str, Any]
) -> str:
    """
    Calculate confidence score for an insight.
    
    Args:
        rule_result: Result from rule evaluation
        data_quality: Data quality metrics
        
    Returns:
        Confidence level: 'high', 'medium', or 'low'
    """
    score = 0.0
    
    # Data completeness (0-0.4)
    completeness = data_quality.get('completeness', 0)
    score += completeness * 0.4
    
    # Statistical significance (0-0.3)
    significance = rule_result.get('significance', 0)
    score += significance * 0.3
    
    # Rule match strength (0-0.3)
    match_strength = rule_result.get('match_strength', 0)
    score += match_strength * 0.3
    
    # Map to confidence level
    if score >= 0.7:
        return 'high'
    elif score >= 0.4:
        return 'medium'
    else:
        return 'low'
