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
            'next_steps': _generate_next_steps(),
            'bundle_opportunities': _generate_bundle_opportunities(best_sellers_data, profitability_data)
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
    
    # Buy Now: Multiple criteria for better recommendations
    inventory_lookup = {item.get('product_id'): item for item in inventory}
    buy_candidates = []
    
    # Strategy 1: High velocity + low stock (top sellers running out)
    for product in best_sellers[:15]:
        product_id = product.get('product_id')
        if product_id and product_id in inventory_lookup:
            stock = inventory_lookup[product_id].get('current_stock', 0)
            velocity = inventory_lookup[product_id].get('velocity', 0)
            qty_sold = product.get('total_quantity', 0)
            avg_daily = inventory_lookup[product_id].get('avg_daily_sales', 0)
            days_of_stock = inventory_lookup[product_id].get('days_of_stock', 999)
            
            # Multiple conditions for buying
            if (stock < qty_sold * 0.2 or days_of_stock < 14 or stock == 0) and velocity > 0:
                buy_candidates.append({
                    'item': product.get('product_name', 'Unknown'),
                    'quantity': f"{int(max(qty_sold * 0.3, avg_daily * 14))} units",
                    'reason': f"🚨 URGENT: Only {int(stock)} units left! Sells {avg_daily:.1f} units/day. Stock will run out in {int(days_of_stock)} days. Order NOW to avoid stockout!",
                    'priority': 'high',
                    'urgency_score': 100 - days_of_stock if days_of_stock < 30 else 50
                })
    
    # Strategy 2: Medium velocity products with very low stock
    for product in best_sellers[10:25]:  # Next tier sellers
        product_id = product.get('product_id')
        if product_id and product_id in inventory_lookup:
            stock = inventory_lookup[product_id].get('current_stock', 0)
            velocity = inventory_lookup[product_id].get('velocity', 0)
            qty_sold = product.get('total_quantity', 0)
            avg_daily = inventory_lookup[product_id].get('avg_daily_sales', 0)
            days_of_stock = inventory_lookup[product_id].get('days_of_stock', 999)
            
            if stock > 0 and days_of_stock < 21 and velocity > 0 and qty_sold > 10:
                buy_candidates.append({
                    'item': product.get('product_name', 'Unknown'),
                    'quantity': f"{int(avg_daily * 21)} units",
                    'reason': f"⚠️ Low stock alert: {int(stock)} units remaining. Reorder to maintain 3-week supply.",
                    'priority': 'medium',
                    'urgency_score': 70 - days_of_stock
                })
    
    # Strategy 3: Products with high reorder score from inventory intelligence
    for item in inventory:
        reorder_score = item.get('reorder_score', 0)
        product_id = item.get('product_id')
        product_name = item.get('product_name', 'Unknown')
        
        # Skip if already in buy_candidates
        if any(c['item'] == product_name for c in buy_candidates):
            continue
            
        if reorder_score >= 60:
            stock = item.get('current_stock', 0)
            avg_daily = item.get('avg_daily_sales', 0)
            days_of_stock = item.get('days_of_stock', 999)
            
            buy_candidates.append({
                'item': product_name,
                'quantity': f"{int(avg_daily * 14)} units" if avg_daily > 0 else "Review stock",
                'reason': f"📊 Smart reorder: High demand detected. Current stock: {int(stock)} units. Recommended order: {int(avg_daily * 14)} units for 2-week supply.",
                'priority': 'medium',
                'urgency_score': reorder_score
            })
    
    # Sort by urgency and take top 8
    buy_candidates.sort(key=lambda x: x.get('urgency_score', 0), reverse=True)
    action_plan['buy_now'] = buy_candidates[:8]
    
    # Promote These: High margin products not in top sellers with specific actions
    top_seller_ids = {p.get('product_id') for p in best_sellers[:10]}
    promote_candidates = []
    
    for item in profitability[:30]:
        product_id = item.get('product_id')
        margin = item.get('profit_margin', 0)
        revenue = item.get('revenue', 0)
        product_name = item.get('product_name', 'Unknown')
        
        if margin > 15 and product_id not in top_seller_ids and revenue > 2000:
            # Determine promotion strategy based on margin
            if margin > 30:
                strategy = f"🌟 PREMIUM MARGIN ({margin:.0f}%): This is a profit goldmine!"
                actions = [
                    f"1. Move to eye-level shelf (chest to eye height)",
                    f"2. Create 'Featured Product' display near entrance",
                    f"3. Train staff to recommend this product",
                    f"4. Consider small bundle: Buy 2 get 10% off"
                ]
            elif margin > 25:
                strategy = f"💎 HIGH MARGIN ({margin:.0f}%): Great profit opportunity!"
                actions = [
                    f"1. Place next to checkout counter",
                    f"2. Add 'Best Value' tag",
                    f"3. Mention in customer conversations"
                ]
            else:
                strategy = f"✅ GOOD MARGIN ({margin:.0f}%): Boost visibility!"
                actions = [
                    f"1. Display in high-traffic area",
                    f"2. Pair with complementary best-seller"
                ]
            
            promote_candidates.append({
                'item': product_name,
                'margin': f"{margin:.1f}%",
                'revenue': f"₹{revenue:,.0f}",
                'suggestion': f"{strategy}\n" + "\n".join(actions),
                'priority_score': margin * (revenue / 1000)  # Higher margin + revenue = higher priority
            })
    
    # Sort by priority and take top 5
    promote_candidates.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
    action_plan['promote_these'] = promote_candidates[:5]
    
    # Cut These: Dead stock items with actionable steps
    total_dead_value = 0
    for item in dead_stock[:8]:  # Show more items
        days = item.get('days_since_sale', 0)
        value = item.get('estimated_value', 0)
        stock = item.get('current_stock', 0)
        product_name = item.get('product_name', 'Unknown')
        
        if days > 90 and stock > 0:
            # Determine action based on value and days
            if value > 10000:
                action = f"💰 HIGH VALUE STUCK: ₹{value:,.0f} tied up! Take immediate action:"
                steps = [
                    f"1. Offer 20-25% discount this week",
                    f"2. Create bundle: Pair with '{best_sellers[0].get('product_name', 'top seller') if best_sellers else 'best-seller'}' at 15% off bundle",
                    f"3. If no movement in 2 weeks, increase discount to 30-35%"
                ]
            elif value > 5000:
                action = f"⚠️ Moderate value stuck: ₹{value:,.0f}. Action plan:"
                steps = [
                    f"1. Display prominently near checkout counter",
                    f"2. Offer 15-20% discount",
                    f"3. Bundle with fast-moving items"
                ]
            else:
                action = f"📦 Low value stock: ₹{value:,.0f}. Quick action:"
                steps = [
                    f"1. Offer 20% discount immediately",
                    f"2. Consider clearance sale if no movement in 1 week"
                ]
            
            action_plan['cut_these'].append({
                'item': product_name,
                'days': f"{int(days)} days",
                'value': f"₹{value:,.0f}",
                'stock': f"{int(stock)} units",
                'suggestion': f"{action}\n" + "\n".join(steps)
            })
            total_dead_value += value
            
            if len(action_plan['cut_these']) >= 5:
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
    """Generate intelligent sales forecast using trends and patterns."""
    if not best_sellers:
        return "Upload data to see sales forecasts!"
    
    # Use trends data if available
    trend_direction = None
    trend_percent = 0
    if trends and trends.get('results'):
        recent_trends = trends['results'][:2]  # Last 2 months
        if len(recent_trends) >= 2:
            current_value = recent_trends[0].get('value', 0)
            previous_value = recent_trends[1].get('value', 0)
            if previous_value > 0:
                change_pct = ((current_value - previous_value) / previous_value) * 100
                trend_percent = abs(change_pct)
                if change_pct > 5:
                    trend_direction = "growing"
                elif change_pct < -5:
                    trend_direction = "declining"
                else:
                    trend_direction = "stable"
    
    # Check for seasonal spike
    current_month = datetime.now().month
    seasonal_boost = None
    for item in seasonal:
        peak_months = item.get('peak_months', [])
        seasonality_score = item.get('seasonality_score', 0)
        if current_month in peak_months and seasonality_score > 0.6:
            forecast_pct = int(seasonality_score * 50)
            seasonal_boost = {
                'product': item.get('product_name', 'seasonal items'),
                'boost': forecast_pct
            }
            break
    
    # Build forecast message
    top_product = best_sellers[0]
    product_name = top_product.get('product_name', 'top products')
    qty = top_product.get('total_quantity', 0)
    avg_daily = qty / 30 if qty > 0 else 0
    
    forecast_parts = []
    
    if seasonal_boost:
        forecast_parts.append(
            f"🌦️ SEASONAL BOOST: Expect {seasonal_boost['boost']}% surge in {seasonal_boost['product']} sales this month! Stock up now to capitalize."
        )
    
    if trend_direction == "growing":
        forecast_parts.append(
            f"📈 TRENDING UP: Sales are {trend_percent:.0f}% higher than last month! Continue promoting top sellers like '{product_name}' to maintain momentum."
        )
    elif trend_direction == "declining":
        forecast_parts.append(
            f"⚠️ SLOWDOWN ALERT: Sales dropped {trend_percent:.0f}% from last month. Take action: {product_name} needs promotion or bundle deals to recover."
        )
    elif avg_daily > 10:
        forecast_parts.append(
            f"✅ STEADY FLOW: {product_name} sells ~{avg_daily:.0f} units/day consistently. Maintain current stock levels and watch for weekly patterns."
        )
    else:
        forecast_parts.append(
            f"💡 OPPORTUNITY: {product_name} has room to grow. Consider promotional pricing or cross-selling with complementary products."
        )
    
    # Add actionable forecast
    if avg_daily > 0:
        weekly_estimate = avg_daily * 7
        forecast_parts.append(
            f"📊 NEXT 7 DAYS: Projected ~{weekly_estimate:.0f} units of {product_name}. Plan inventory accordingly."
        )
    
    return " | ".join(forecast_parts) if forecast_parts else "Monitor your sales patterns to optimize inventory and promotions."


def _generate_next_steps() -> str:
    """Generate actionable next steps based on shop state."""
    steps = [
        "1️⃣ Update inventory: Enter today's new stock to keep recommendations accurate",
        "2️⃣ Act on Buy Now items: Order the top 3 urgent items within 24 hours",
        "3️⃣ Start promotions: Pick 1 product from 'Promote These' and display it prominently today",
        "4️⃣ Review daily: Check tomorrow's sales to see if promotions are working"
    ]
    return " | ".join(steps)


def _generate_bundle_opportunities(best_sellers: List[Dict[str, Any]], profitability: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Identify products that could be bundled together."""
    bundles = []
    
    # Simple heuristic: Pair high-margin with slow-moving products
    top_seller_names = {p.get('product_name') for p in best_sellers[:5]}
    
    profitability_sorted = sorted(profitability, key=lambda x: x.get('revenue', 0), reverse=True)
    
    # Find slow-moving but high-margin products
    for item in profitability_sorted[:15]:
        product_name = item.get('product_name', '')
        revenue = item.get('revenue', 0)
        margin = item.get('profit_margin', 0)
        
        # Not a top seller but has decent revenue and margin
        if product_name not in top_seller_names and margin > 15 and revenue > 2000:
            # Suggest bundling with a top seller
            if best_sellers:
                top_seller = best_sellers[0].get('product_name', 'items')
                bundles.append({
                    'item1': top_seller,
                    'item2': product_name,
                    'suggestion': f"Bundle {top_seller} with {product_name} - increase visibility of your {margin:.0f}% margin product!"
                })
                if len(bundles) >= 2:
                    break
    
    return bundles
