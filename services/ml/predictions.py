"""Machine Learning-based predictions for sales forecasting and demand prediction."""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from storage.database import Database
from storage.cache import CacheManager
from utils.logging import setup_logging

logger = setup_logging()


async def predict_sales_forecast(
    db: Database,
    cache: CacheManager,
    dataset_id: str,
    days_ahead: int = 7,
    product_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Predict sales for next N days using time series analysis.
    
    Uses simple moving average and trend analysis for forecasting.
    
    Args:
        db: Database instance
        cache: Cache manager instance
        dataset_id: Dataset identifier
        days_ahead: Number of days to predict (default: 7)
        product_id: Optional specific product to forecast
        
    Returns:
        Dictionary with predictions and confidence scores
    """
    # Get sales data
    query = """
        SELECT 
            date,
            product_id,
            product_name,
            SUM(quantity) as daily_quantity,
            SUM(total_amount) as daily_revenue
        FROM raw_sales
        WHERE dataset_id = ?
    """
    params = [dataset_id]
    
    if product_id:
        query += " AND product_id = ?"
        params.append(product_id)
    
    query += " GROUP BY date, product_id, product_name ORDER BY date ASC"
    
    rows = await db.execute_query(query, tuple(params))
    
    if not rows or len(rows) < 7:
        return {
            'predictions': [],
            'method': 'insufficient_data',
            'confidence': 'low'
        }
    
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    predictions = []
    
    # Group by product for individual predictions
    for product_id_val in df['product_id'].unique() if 'product_id' in df.columns else [None]:
        product_data = df[df['product_id'] == product_id_val] if product_id_val else df
        
        # Get last 30 days of data (or all if less)
        recent_data = product_data.tail(30)
        
        if len(recent_data) < 3:
            continue
        
        # Calculate moving averages
        ma_7 = recent_data['daily_quantity'].tail(7).mean()
        ma_14 = recent_data['daily_quantity'].tail(14).mean() if len(recent_data) >= 14 else ma_7
        
        # Calculate trend (slope)
        recent_quantities = recent_data['daily_quantity'].tail(7).values
        if len(recent_quantities) >= 3:
            x = np.arange(len(recent_quantities))
            trend_slope = np.polyfit(x, recent_quantities, 1)[0] if len(recent_quantities) >= 2 else 0
        else:
            trend_slope = 0
        
        # Predict next days
        last_date = recent_data['date'].max()
        base_prediction = ma_7
        confidence = 'medium'
        
        # Adjust confidence based on data consistency
        std_dev = recent_data['daily_quantity'].tail(7).std()
        mean_qty = recent_data['daily_quantity'].tail(7).mean()
        coefficient_of_variation = std_dev / mean_qty if mean_qty > 0 else 1
        
        if coefficient_of_variation < 0.3:
            confidence = 'high'
        elif coefficient_of_variation > 0.7:
            confidence = 'low'
        
        # Generate predictions
        for i in range(1, days_ahead + 1):
            pred_date = last_date + timedelta(days=i)
            # Apply trend adjustment (diminishing effect over time)
            trend_adjustment = trend_slope * (1 - 0.1 * i)  # Trend weakens over time
            predicted_qty = max(0, base_prediction + trend_adjustment)
            
            # Predict revenue based on average price
            avg_price = recent_data['daily_revenue'].sum() / recent_data['daily_quantity'].sum() if recent_data['daily_quantity'].sum() > 0 else 0
            predicted_revenue = predicted_qty * avg_price
            
            predictions.append({
                'date': pred_date.strftime('%Y-%m-%d'),
                'product_id': product_id_val,
                'product_name': product_data['product_name'].iloc[0] if len(product_data) > 0 else 'All Products',
                'predicted_quantity': round(float(predicted_qty), 2),
                'predicted_revenue': round(float(predicted_revenue), 2),
                'confidence': confidence,
                'method': 'moving_average_with_trend'
            })
    
    return {
        'predictions': predictions,
        'method': 'moving_average_with_trend',
        'confidence': 'medium',
        'days_ahead': days_ahead
    }


async def detect_anomalies(
    db: Database,
    cache: CacheManager,
    dataset_id: str,
    threshold: float = 2.0
) -> List[Dict[str, Any]]:
    """
    Detect anomalies in sales data using statistical methods.
    
    Uses z-score to identify unusual patterns.
    
    Args:
        db: Database instance
        cache: Cache manager instance
        dataset_id: Dataset identifier
        threshold: Z-score threshold (default: 2.0 = 95% confidence)
        
    Returns:
        List of detected anomalies
    """
    # Get daily sales data
    query = """
        SELECT 
            date,
            SUM(quantity) as daily_quantity,
            SUM(total_amount) as daily_revenue
        FROM raw_sales
        WHERE dataset_id = ?
        GROUP BY date
        ORDER BY date ASC
    """
    
    rows = await db.execute_query(query, (dataset_id,))
    
    if not rows or len(rows) < 7:
        return []
    
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    
    anomalies = []
    
    # Calculate z-scores for quantity
    mean_qty = df['daily_quantity'].mean()
    std_qty = df['daily_quantity'].std()
    
    if std_qty > 0:
        df['z_score_qty'] = (df['daily_quantity'] - mean_qty) / std_qty
        
        # Find anomalies
        anomaly_rows = df[df['z_score_qty'].abs() > threshold]
        
        for _, row in anomaly_rows.iterrows():
            anomaly_type = 'spike' if row['z_score_qty'] > 0 else 'drop'
            anomalies.append({
                'date': row['date'].strftime('%Y-%m-%d'),
                'type': anomaly_type,
                'observed_quantity': float(row['daily_quantity']),
                'expected_quantity': float(mean_qty),
                'deviation_percent': float((row['daily_quantity'] - mean_qty) / mean_qty * 100),
                'z_score': float(row['z_score_qty']),
                'severity': 'high' if abs(row['z_score_qty']) > 3 else 'medium'
            })
    
    return anomalies


async def predict_demand(
    db: Database,
    cache: CacheManager,
    dataset_id: str,
    product_id: str,
    days_ahead: int = 30
) -> Dict[str, Any]:
    """
    Predict demand for a specific product.
    
    Args:
        db: Database instance
        cache: Cache manager instance
        dataset_id: Dataset identifier
        product_id: Product identifier
        days_ahead: Days to predict ahead
        
    Returns:
        Demand prediction with recommended stock level
    """
    forecast = await predict_sales_forecast(db, cache, dataset_id, days_ahead, product_id)
    
    if not forecast['predictions']:
        return {
            'product_id': product_id,
            'predicted_demand': 0,
            'recommended_stock': 0,
            'confidence': 'low',
            'message': 'Insufficient data for prediction'
        }
    
    # Sum predictions for total demand
    total_predicted_demand = sum(p['predicted_quantity'] for p in forecast['predictions'])
    avg_daily_demand = total_predicted_demand / days_ahead
    
    # Recommend stock level: 1.5x predicted demand (buffer for variability)
    safety_multiplier = 1.5
    recommended_stock = int(avg_daily_demand * days_ahead * safety_multiplier)
    
    return {
        'product_id': product_id,
        'predicted_demand': round(total_predicted_demand, 2),
        'avg_daily_demand': round(avg_daily_demand, 2),
        'recommended_stock': recommended_stock,
        'confidence': forecast['confidence'],
        'method': 'time_series_forecast',
        'days_ahead': days_ahead
    }
