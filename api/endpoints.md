# API Endpoints Specification

Complete API endpoint documentation with request/response examples.

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Currently none (local-first app). Can add API key authentication later if needed.

---

## Datasets

### Upload Dataset
```http
POST /api/v1/datasets
Content-Type: multipart/form-data

Form Data:
  file: <file>
  name: "Sales Data Q4 2024" (optional)
  source_type: "csv" (optional, auto-detected)
```

**Response:**
```json
{
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Sales Data Q4 2024",
  "status": "processing",
  "row_count": 0,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Errors:**
- `400`: Invalid file format
- `400`: File too large (>100MB)
- `409`: Duplicate file (same hash)

---

### List Datasets
```http
GET /api/v1/datasets?status=completed&source_type=csv
```

**Query Parameters:**
- `status`: Filter by status (pending, processing, completed, error)
- `source_type`: Filter by type (csv, pdf, vyapar)
- `limit`: Max results (default: 50)
- `offset`: Pagination offset

**Response:**
```json
{
  "datasets": [
    {
      "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Sales Data Q4 2024",
      "source_type": "csv",
      "status": "completed",
      "row_count": 15234,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:32:15Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

### Get Dataset Details
```http
GET /api/v1/datasets/{dataset_id}
```

**Response:**
```json
{
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Sales Data Q4 2024",
  "source_type": "csv",
  "file_path": "/data/uploads/sales_q4.csv",
  "status": "completed",
  "row_count": 15234,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:32:15Z",
  "error_message": null
}
```

**Errors:**
- `404`: Dataset not found

---

### Delete Dataset
```http
DELETE /api/v1/datasets/{dataset_id}
```

**Response:**
```json
{
  "success": true,
  "message": "Dataset deleted successfully"
}
```

**Errors:**
- `404`: Dataset not found

---

## Analytics

### Best Sellers
```http
GET /api/v1/analytics/{dataset_id}/best-sellers?limit=10&period=2024-01
```

**Query Parameters:**
- `limit`: Number of results (default: 10, max: 100)
- `period`: Filter by period (YYYY-MM format, optional)
- `sort_by`: "quantity" or "revenue" (default: "quantity")

**Response:**
```json
{
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "analytics_type": "best_sellers",
  "period": "2024-01",
  "results": [
    {
      "product_name": "Rice 5kg",
      "product_id": "PROD001",
      "total_quantity": 450.0,
      "total_revenue": 22500.0,
      "rank": 1,
      "category": "Food"
    },
    {
      "product_name": "Wheat Flour 2kg",
      "product_id": "PROD002",
      "total_quantity": 320.0,
      "total_revenue": 12800.0,
      "rank": 2,
      "category": "Food"
    }
  ],
  "computed_at": "2024-01-15T10:35:00Z",
  "cached": true
}
```

---

### Revenue Contribution
```http
GET /api/v1/analytics/{dataset_id}/revenue-contribution?limit=20
```

**Response:**
```json
{
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "analytics_type": "revenue_contribution",
  "total_revenue": 125000.0,
  "results": [
    {
      "product_name": "Rice 5kg",
      "product_id": "PROD001",
      "revenue": 22500.0,
      "percentage": 18.0,
      "rank": 1,
      "category": "Food"
    }
  ],
  "computed_at": "2024-01-15T10:36:00Z",
  "cached": true
}
```

---

### Seasonality
```http
GET /api/v1/analytics/{dataset_id}/seasonality?min_seasonality_score=0.3
```

**Response:**
```json
{
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "analytics_type": "seasonality",
  "results": [
    {
      "product_name": "Umbrella",
      "product_id": "PROD050",
      "seasonality_score": 0.75,
      "peak_months": [6, 7, 8],
      "low_months": [11, 12, 1],
      "category": "Seasonal"
    }
  ],
  "computed_at": "2024-01-15T10:37:00Z",
  "cached": true
}
```

---

### Inventory Velocity
```http
GET /api/v1/analytics/{dataset_id}/inventory-velocity
```

**Response:**
```json
{
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "analytics_type": "inventory_velocity",
  "results": [
    {
      "product_name": "Rice 5kg",
      "product_id": "PROD001",
      "velocity_score": "high",
      "turnover_rate": 12.5,
      "avg_days_in_stock": 29.2,
      "category": "Food"
    },
    {
      "product_name": "Old Stock Item",
      "product_id": "PROD099",
      "velocity_score": "low",
      "turnover_rate": 0.1,
      "avg_days_in_stock": 365.0,
      "category": "Misc"
    }
  ],
  "computed_at": "2024-01-15T10:38:00Z",
  "cached": true
}
```

---

### Dead Stock
```http
GET /api/v1/analytics/{dataset_id}/dead-stock?days_threshold=90
```

**Response:**
```json
{
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "analytics_type": "dead_stock",
  "threshold_days": 90,
  "results": [
    {
      "product_name": "Old Stock Item",
      "product_id": "PROD099",
      "days_since_sale": 120,
      "current_stock": 50.0,
      "unit_cost": 100.0,
      "estimated_value": 5000.0,
      "category": "Misc"
    }
  ],
  "computed_at": "2024-01-15T10:39:00Z",
  "cached": true
}
```

---

### Profitability
```http
GET /api/v1/analytics/{dataset_id}/profitability
```

**Response:**
```json
{
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "analytics_type": "profitability",
  "results": [
    {
      "product_name": "Premium Product",
      "product_id": "PROD100",
      "revenue": 50000.0,
      "cost": 30000.0,
      "profit": 20000.0,
      "profit_margin": 40.0,
      "rank": 1,
      "category": "Premium"
    }
  ],
  "computed_at": "2024-01-15T10:40:00Z",
  "cached": true
}
```

---

### Trends
```http
GET /api/v1/analytics/{dataset_id}/trends?metric=revenue&months=6
```

**Query Parameters:**
- `metric`: "revenue", "quantity", or "profit" (default: "revenue")
- `months`: Number of months (default: 6, max: 24)

**Response:**
```json
{
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "analytics_type": "trends",
  "metric": "revenue",
  "results": [
    {
      "month": "2024-01",
      "value": 125000.0,
      "change_percent": 5.2,
      "trend": "up",
      "previous_month": "2023-12",
      "previous_value": 118750.0
    },
    {
      "month": "2023-12",
      "value": 118750.0,
      "change_percent": -2.1,
      "trend": "down",
      "previous_month": "2023-11",
      "previous_value": 121300.0
    }
  ],
  "computed_at": "2024-01-15T10:41:00Z",
  "cached": true
}
```

---

## Insights

### Get All Insights
```http
GET /api/v1/insights/{dataset_id}?category=risk&confidence=high&limit=10
```

**Query Parameters:**
- `category`: Filter by category (growth, risk, efficiency)
- `confidence`: Filter by confidence (high, medium, low)
- `limit`: Max results (default: 50)
- `offset`: Pagination offset

**Response:**
```json
{
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "insights": [
    {
      "id": 1,
      "insight_id": "dead_stock_PROD099",
      "title": "Dead Stock: Old Stock Item",
      "category": "risk",
      "confidence": "high",
      "supporting_metrics": {
        "days_since_sale": 120,
        "current_stock": 50.0,
        "estimated_value": 5000.0
      },
      "recommended_action": "Consider discounting or discontinuing Old Stock Item. Stock value: ₹5000",
      "generated_at": "2024-01-15T10:45:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

### Get Specific Insight
```http
GET /api/v1/insights/{dataset_id}/{insight_id}
```

**Response:**
```json
{
  "id": 1,
  "insight_id": "dead_stock_PROD099",
  "title": "Dead Stock: Old Stock Item",
  "category": "risk",
  "confidence": "high",
  "supporting_metrics": {
    "days_since_sale": 120,
    "current_stock": 50.0,
    "estimated_value": 5000.0,
    "category": "Misc"
  },
  "recommended_action": "Consider discounting or discontinuing Old Stock Item. Stock value: ₹5000",
  "generated_at": "2024-01-15T10:45:00Z",
  "is_active": true
}
```

**Errors:**
- `404`: Insight not found

---

## AI Explanations

### Generate Explanation
```http
POST /api/v1/ai/explain
Content-Type: application/json

{
  "dataset_id": "550e8400-e29b-41d4-a716-446655440000",
  "insight_ids": [1, 2, 3],
  "include_guidance": true
}
```

**Request Body:**
- `dataset_id`: Required
- `insight_ids`: Optional list of specific insight IDs (if empty, uses all insights)
- `include_guidance`: Include business guidance (default: true)

**Response:**
```json
{
  "explanation": "Your business shows several key patterns. The top-selling product, Rice 5kg, contributes 18% of total revenue, indicating strong customer demand. However, there's a risk with Old Stock Item, which hasn't sold in 120 days and represents ₹5000 in tied-up capital.",
  "guidance": "Focus on promoting high-velocity products like Rice 5kg. For dead stock items, consider running a clearance sale to free up capital. Monitor seasonal products like Umbrella as monsoon season approaches.",
  "insights_covered": [1, 2, 3],
  "model_used": "gpt-4",
  "generated_at": "2024-01-15T10:50:00Z",
  "cached": false
}
```

**Errors:**
- `400`: Invalid dataset_id
- `400`: No insights available
- `503`: AI service unavailable
- `500`: AI service error

---

### Get Cached Explanation
```http
GET /api/v1/ai/explanations/{insight_id}
```

**Response:**
```json
{
  "insight_id": 1,
  "explanation": "Old Stock Item represents a dead stock risk...",
  "guidance": "Consider discounting or discontinuing...",
  "model_used": "gpt-4",
  "generated_at": "2024-01-15T10:50:00Z"
}
```

**Errors:**
- `404`: Explanation not found

---

## System

### Health Check
```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected",
  "cache_stats": {
    "total_entries": 45,
    "total_size_mb": 12.5,
    "oldest_entry": "2024-01-10T08:00:00Z"
  },
  "ai_service": "available"
}
```

---

### Force Recompute Analytics
```http
POST /api/v1/jobs/analytics/{dataset_id}/recompute
```

**Response:**
```json
{
  "job_id": 123,
  "status": "pending",
  "message": "Analytics recomputation queued",
  "estimated_completion": "2024-01-15T10:55:00Z"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Dataset not found",
    "details": {
      "dataset_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  }
}
```

**Common Error Codes:**
- `VALIDATION_ERROR`: Request validation failed
- `RESOURCE_NOT_FOUND`: Resource doesn't exist
- `DUPLICATE_RESOURCE`: Resource already exists
- `PROCESSING_ERROR`: Error during processing
- `AI_SERVICE_ERROR`: AI service unavailable or error
- `CACHE_ERROR`: Cache operation failed
- `DATABASE_ERROR`: Database operation failed
