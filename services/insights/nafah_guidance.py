"""Nafah Guidance - Expert AI sales advisor for shopkeepers."""

from typing import List, Dict, Any
from datetime import datetime, timedelta


def generate_nafah_guidance(
    best_sellers_data: List[Dict[str, Any]],
    dead_stock_data: List[Dict[str, Any]],
    profitability_data: List[Dict[str, Any]],
    inventory_data: List[Dict[str, Any]],
    seasonal_data: List[Dict[str, Any]],
    trends_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive Nafah Guidance report in shopkeeper-friendly format.
    
    Args:
        best_sellers_data: Top selling products
        dead_stock_data: Dead stock items
        profitability_data: Profitability data
        inventory_data: Inventory velocity data
        seasonal_data: Seasonal patterns
        trends_data: Sales trends data (optional)
        
    Returns:
        Comprehensive guidance insight dict
    """
    guidance = {
        'insight_id': 'nafah_guidance_main',
        'title': "Nafah's Guidance",
        'category': 'guidance',
        'confidence': 'high',
        'guidance_format': {
            'quick_summary': _generate_quick_summary(best_sellers_data, dead_stock_data, profitability_data),
            'best_sellers_breakdown': _generate_best_sellers_table(best_sellers_data[:5]),
            'action_plan': _generate_action_plan(
                best_sellers_data,
                dead_stock_data,
                profitability_data,
                inventory_data,
                seasonal_data
            ),
            'forecast': _generate_forecast(best_sellers_data, seasonal_data, trends_data),
            'next_steps': _generate_next_steps()
        }
    }
    
    return guidance


def _generate_quick_summary(
    best_sellers: List[Dict[str, Any]],
    dead_stock: List[Dict[str, Any]],
    profitability: List[Dict[str, Any]]
) -> str:
    """Generate quick summary line."""
    if not best_sellers:
        return "Upload your sales data to see Nafah's personalized advice for your shop!"
    
    # Calculate total revenue (approximate for week)
    total_revenue = sum(item.get('total_amount', 0) or item.get('total_revenue', 0) for item in best_sellers[:10])
    
    # Get top 3 products
    top_3 = [item.get('product_name', 'Unknown') for item in best_sellers[:3]]
    
    # Get bottom performers (dead stock or low revenue)
    bottom_2 = []
    if dead_stock:
        bottom_2 = [item.get('product_name', 'Unknown') for item in dead_stock[:2]]
    elif profitability:
        # Find low-revenue items
        low_revenue = sorted(profitability, key=lambda x: x.get('revenue', 0))[:2]
        bottom_2 = [item.get('product_name', 'Unknown') for item in low_revenue]
    
    stars_str = ", ".join(top_3)
    fix_str = ", ".join(bottom_2) if bottom_2 else "None - great job!"
    
    return f"Your shop's top performers: {stars_str}. Need attention: {fix_str}."


def _generate_best_sellers_table(best_sellers: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Generate best-sellers breakdown table."""
    table = []
    
    for item in best_sellers:
        product_name = item.get('product_name', 'Unknown')
        total_qty = item.get('total_quantity', 0)
        total_revenue = item.get('total_amount', 0) or item.get('total_revenue', 0)
        
        # Determine trend (simplified - could be improved with actual trend data)
        if total_qty > 100:
            trend = "🔥 Hot"
        elif total_qty > 50:
            trend = "📈 Up"
        else:
            trend = "✓ Steady"
        
        table.append({
            'product': product_name,
            'sold': f"{total_qty:.0f}",
            'revenue': f"₹{total_revenue:,.0f}",
            'trend': trend
        })
    
    return table


def _generate_action_plan(
    best_sellers: List[Dict[str, Any]],
    dead_stock: List[Dict[str, Any]],
    profitability: List[Dict[str, Any]],
    inventory: List[Dict[str, Any]],
    seasonal: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate action plan sections."""
    action_plan = {
        'buy_now': [],
        'promote_these': [],
        'cut_these': [],
        'seasonal_tip': None
    }
    
    # Buy Now: High velocity, low stock items
    inventory_lookup = {item.get('product_id'): item for item in inventory}
    for product in best_sellers[:10]:
        product_id = product.get('product_id')
        if product_id and product_id in inventory_lookup:
            stock = inventory_lookup[product_id].get('current_stock', 0)
            velocity = inventory_lookup[product_id].get('velocity', 0)
            qty_sold = product.get('total_quantity', 0)
            
            if stock < qty_sold * 0.2 and velocity > 0:  # Less than 20% of monthly sales
                action_plan['buy_now'].append({
                    'item': product.get('product_name', 'Unknown'),
                    'quantity': f"{int(qty_sold * 0.3)} units",
                    'reason': f"Flying off shelves! Only {stock} left, sells {velocity:.1f} units/day"
                })
                
                if len(action_plan['buy_now']) >= 5:
                    break
    
    # Promote These: High margin products not in top sellers
    top_seller_ids = {p.get('product_id') for p in best_sellers[:10]}
    for item in profitability[:20]:
        product_id = item.get('product_id')
        margin = item.get('profit_margin', 0)
        revenue = item.get('revenue', 0)
        
        if margin > 20 and product_id not in top_seller_ids and revenue > 3000:
            action_plan['promote_these'].append({
                'item': item.get('product_name', 'Unknown'),
                'margin': f"{margin:.1f}%",
                'suggestion': f"Place at eye-level or create bundle deals - this {margin:.0f}% margin gem needs more visibility!"
            })
            
            if len(action_plan['promote_these']) >= 3:
                break
    
    # Cut These: Dead stock items
    total_dead_value = 0
    for item in dead_stock[:5]:
        days = item.get('days_since_sale', 0)
        value = item.get('estimated_value', 0)
        stock = item.get('current_stock', 0)
        
        if days > 90 and stock > 0:
            discount = "15-20%" if days < 180 else "25-30%"
            action_plan['cut_these'].append({
                'item': item.get('product_name', 'Unknown'),
                'days': f"{int(days)} days",
                'value': f"₹{value:,.0f}",
                'suggestion': f"Offer {discount} discount or bundle with best-sellers. {int(days)} days without sale - capital stuck!"
            })
            total_dead_value += value
            
            if len(action_plan['cut_these']) >= 3:
                break
    
    # Seasonal Tip
    current_month = datetime.now().month
    for item in seasonal:
        peak_months = item.get('peak_months', [])
        seasonality_score = item.get('seasonality_score', 0)
        
        if seasonality_score > 0.6 and peak_months:
            # Find next peak
            next_peak = None
            for peak_month in sorted(peak_months):
                if peak_month >= current_month:
                    next_peak = peak_month
                    break
            
            if next_peak:
                months_away = next_peak - current_month
                if months_away <= 2:
                    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                    action_plan['seasonal_tip'] = (
                        f"🌦️ Peak season for {item.get('product_name', 'seasonal items')} "
                        f"approaching in {months_away} month(s)! Stock up by {month_names[next_peak-1]} "
                        f"to catch the {seasonality_score*100:.0f}% demand surge."
                    )
                    break
    
    return action_plan


def _generate_forecast(
    best_sellers: List[Dict[str, Any]],
    seasonal: List[Dict[str, Any]],
    trends: Dict[str, Any] = None
) -> str:
    """Generate sales forecast."""
    if not best_sellers:
        return "Upload data to see sales forecasts!"
    
    # Simple forecast based on current top seller
    top_product = best_sellers[0]
    product_name = top_product.get('product_name', 'top products')
    qty = top_product.get('total_quantity', 0)
    
    # Check for seasonal spike
    current_month = datetime.now().month
    for item in seasonal:
        peak_months = item.get('peak_months', [])
        if current_month in peak_months:
            seasonality_score = item.get('seasonality_score', 0)
            if seasonality_score > 0.6:
                forecast_pct = int(seasonality_score * 50)
                return f"Next week: Expect {forecast_pct}% more sales on {item.get('product_name', 'seasonal items')} due to seasonal demand!"
    
    # Default forecast
    avg_daily = qty / 30 if qty > 0 else 0
    if avg_daily > 10:
        return f"Next week: Expect steady sales of {product_name} (~{avg_daily:.0f} units/day). Stock levels look good!"
    else:
        return "Next week: Monitor sales patterns - consider promotional activities to boost mid-week sales."


def _generate_next_steps() -> str:
    """Generate next steps."""
    return "📱 Quick win: Scan your new stock entries today to keep Nafah's advice fresh and accurate!"
