"""Main insights engine."""

import json
from typing import List, Dict, Any
from storage.database import Database
from services.analytics import (
    dead_stock,
    seasonality,
    best_sellers,
    profitability,
    inventory
)
from services.insights.rules import risk_rules, growth_rules, efficiency_rules
from services.insights.rules import profitability_rules
from services.insights.scorer import score_confidence
from utils.logging import setup_logging

logger = setup_logging()


async def generate_insights(
    db: Database,
    cache,
    dataset_id: str
) -> List[Dict[str, Any]]:
    """
    Generate all insights for a dataset.
    
    Args:
        db: Database instance
        cache: Cache manager instance
        dataset_id: Dataset identifier
        
    Returns:
        List of generated insights
    """
    logger.info(f"Generating insights for dataset {dataset_id}")
    
    # Load analytics data
    dead_stock_data = await dead_stock.compute_dead_stock(db, cache, dataset_id)
    seasonal_data = await seasonality.compute_seasonality(db, cache, dataset_id)
    best_sellers_data = await best_sellers.compute_best_sellers(db, cache, dataset_id, limit=20)
    profitability_data = await profitability.compute_profitability(db, cache, dataset_id)
    inventory_data = await inventory.compute_inventory_velocity(db, cache, dataset_id)
    
    insights = []
    
    # Evaluate risk rules
    insights.extend(risk_rules.evaluate_dead_stock_rule(dead_stock_data))
    
    # Evaluate growth rules
    insights.extend(growth_rules.evaluate_seasonal_peak_rule(seasonal_data))
    insights.extend(
        growth_rules.evaluate_high_velocity_low_stock_rule(best_sellers_data, inventory_data)
    )
    
    # Evaluate efficiency rules
    insights.extend(efficiency_rules.evaluate_low_margin_rule(profitability_data))
    
    # Evaluate profitability rules
    insights.extend(profitability_rules.evaluate_high_profit_opportunity(profitability_data, best_sellers_data))
    insights.extend(profitability_rules.evaluate_profit_concentration(best_sellers_data, profitability_data))
    
    # Generate main Nafah Guidance (comprehensive shopkeeper-friendly report)
    nafah_guidance = generate_nafah_guidance(
        best_sellers_data,
        dead_stock_data,
        profitability_data,
        inventory_data,
        seasonal_data
    )
    insights.insert(0, nafah_guidance)  # Put main guidance first
    
    # Store insights in database
    for insight in insights:
        # Calculate final confidence with data quality
        data_quality = {'completeness': 0.8}  # TODO: Calculate actual data quality
        insight['confidence'] = score_confidence(insight, data_quality)
        
        # Store in database
        # Handle guidance_format for Nafah Guidance
        supporting_metrics = insight.get('supporting_metrics', {})
        if 'guidance_format' in insight:
            supporting_metrics = insight['guidance_format']
        
        recommended_action = insight.get('recommended_action', '')
        if not recommended_action and 'guidance_format' in insight:
            # For Nafah Guidance, use quick_summary as recommended_action
            guidance = insight['guidance_format']
            recommended_action = guidance.get('quick_summary', 'Nafah Guidance available')
        
        await db.execute_write(
            """INSERT INTO insights 
               (dataset_id, insight_id, title, category, confidence, 
                supporting_metrics, recommended_action)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                dataset_id,
                insight['insight_id'],
                insight['title'],
                insight['category'],
                insight['confidence'],
                json.dumps(supporting_metrics),
                recommended_action
            )
        )
    
    logger.info(f"Generated {len(insights)} insights for dataset {dataset_id}")
    
    return insights


async def get_insights(
    db: Database,
    dataset_id: str,
    category: str = None,
    confidence: str = None,
    limit: int = 50,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get stored insights for a dataset.
    
    Args:
        db: Database instance
        dataset_id: Dataset identifier
        category: Optional category filter
        confidence: Optional confidence filter
        limit: Maximum results
        offset: Pagination offset
        
    Returns:
        List of insights
    """
    conditions = ["dataset_id = ?", "is_active = 1"]
    params = [dataset_id]
    
    if category:
        conditions.append("category = ?")
        params.append(category)
    if confidence:
        conditions.append("confidence = ?")
        params.append(confidence)
    
    where_clause = " AND ".join(conditions)
    query = f"""
        SELECT * FROM insights
        WHERE {where_clause}
        ORDER BY 
            CASE confidence 
                WHEN 'high' THEN 1 
                WHEN 'medium' THEN 2 
                WHEN 'low' THEN 3 
            END,
            generated_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    
    rows = await db.execute_query(query, tuple(params))
    
    # Parse JSON fields
    for row in rows:
        if 'supporting_metrics' in row and isinstance(row['supporting_metrics'], str):
            row['supporting_metrics'] = json.loads(row['supporting_metrics'])
    
    return rows
