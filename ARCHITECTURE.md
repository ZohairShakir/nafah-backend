# Lucid Backend Architecture

## System Overview

Lucid backend is a local-first analytics service running alongside the Tauri desktop application. It processes business data deterministically and provides AI-assisted insights through a structured pipeline.

## Core Principles

1. **Deterministic Analytics**: All metrics computed via reproducible algorithms
2. **AI Isolation**: AI never sees raw data, only structured summaries
3. **Local-First**: All processing happens locally, no cloud dependency
4. **Cached Computation**: Analytics cached until source data changes
5. **Fail-Safe**: Graceful degradation, never crashes on bad data

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React/Tauri)                  │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/REST API
┌───────────────────────────▼─────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   API Layer  │  │  Background  │  │   Cache      │     │
│  │   (Routes)   │  │   Jobs       │  │   Manager    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼─────────────┐
│                    Service Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Ingestion  │  │  Analytics   │  │   Insights   │     │
│  │   Service    │  │   Engine     │  │   Engine     │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼─────────────┐
│                    Data Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Storage    │  │   Analytics  │  │   AI Service │     │
│  │   (SQLite)   │  │   Cache      │  │   (OpenAI)   │     │
│  │              │  │   (Parquet)  │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Module Responsibilities

### 1. API Layer (`api/`)
- **Purpose**: HTTP endpoints, request validation, response formatting
- **Responsibilities**:
  - Route definitions
  - Request/response models (Pydantic)
  - Authentication (if needed)
  - Error handling middleware

### 2. Ingestion Service (`services/ingestion/`)
- **Purpose**: Parse and normalize incoming data files
- **Responsibilities**:
  - CSV parsing (sales, inventory, transactions)
  - PDF invoice extraction (structured data)
  - Vyapar export parsing
  - Data validation and cleaning
  - Schema normalization
  - Duplicate detection

### 3. Analytics Engine (`services/analytics/`)
- **Purpose**: Compute deterministic business metrics
- **Responsibilities**:
  - Best-selling products calculation
  - Revenue contribution percentages
  - Seasonal product detection (statistical)
  - Inventory velocity (turnover rate)
  - Dead stock detection (zero movement threshold)
  - Profitability ranking
  - Month-over-month trend analysis
  - All computations cached in Parquet

### 4. Insights Engine (`services/insights/`)
- **Purpose**: Generate rule-based business insights
- **Responsibilities**:
  - Rule evaluation against metrics
  - Insight generation (growth/risk/efficiency)
  - Confidence scoring
  - Supporting metrics collection
  - Action recommendation generation
  - No ML, pure rule-based logic

### 5. AI Service (`services/ai/`)
- **Purpose**: Generate natural language explanations
- **Responsibilities**:
  - Receive structured summaries only
  - Generate explanations from insights
  - Business guidance generation
  - Validation (no invented numbers)
  - Abstraction layer for OpenAI/Claude

### 6. Storage Layer (`storage/`)
- **Purpose**: Data persistence and retrieval
- **Responsibilities**:
  - SQLite database operations
  - Parquet cache management
  - Data versioning
  - Cache invalidation logic

### 7. Background Jobs (`jobs/`)
- **Purpose**: Async processing of heavy operations
- **Responsibilities**:
  - Analytics computation jobs
  - Cache warming
  - Data re-processing on changes
  - Job queue management

## Data Flow

### Ingestion Flow
```
File Upload → Validation → Parser Selection → Parse → Normalize → 
Schema Validation → Store Raw Data → Invalidate Cache → Return Success
```

### Analytics Flow
```
Request Analytics → Check Cache → If Valid: Return Cached
                                    If Invalid: 
                                    → Load Raw Data → 
                                    → Compute Metrics → 
                                    → Store in Parquet → 
                                    → Return Results
```

### Insights Flow
```
Request Insights → Load Analytics → Evaluate Rules → 
Generate Insights → Attach Metrics → Score Confidence → 
Return Structured Insights
```

### AI Explanation Flow
```
Request Explanation → Load Insights → Load Metrics → 
Build Context Object → Call AI Service → Validate Response → 
Return Natural Language Explanation
```

## Database Schema

### Tables (SQLite)

#### `datasets`
- `id` (TEXT PRIMARY KEY) - UUID
- `name` (TEXT) - User-friendly name
- `source_type` (TEXT) - 'csv', 'pdf', 'vyapar'
- `file_path` (TEXT) - Original file location
- `file_hash` (TEXT) - SHA256 for change detection
- `row_count` (INTEGER) - Number of records
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)
- `status` (TEXT) - 'pending', 'processing', 'completed', 'error'

#### `raw_sales`
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `dataset_id` (TEXT, FOREIGN KEY)
- `date` (DATE)
- `product_name` (TEXT)
- `product_id` (TEXT, nullable)
- `quantity` (REAL)
- `unit_price` (REAL)
- `total_amount` (REAL)
- `category` (TEXT, nullable)
- `customer_id` (TEXT, nullable)
- `transaction_id` (TEXT, nullable)
- `created_at` (TIMESTAMP)

#### `raw_inventory`
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `dataset_id` (TEXT, FOREIGN KEY)
- `product_name` (TEXT)
- `product_id` (TEXT, nullable)
- `current_stock` (REAL)
- `unit_cost` (REAL)
- `category` (TEXT, nullable)
- `last_updated` (DATE)
- `created_at` (TIMESTAMP)

#### `analytics_cache`
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `dataset_id` (TEXT, FOREIGN KEY)
- `cache_key` (TEXT) - e.g., 'best_sellers_2024'
- `parquet_path` (TEXT) - Path to cached Parquet file
- `computed_at` (TIMESTAMP)
- `data_hash` (TEXT) - Hash of source data used
- `expires_at` (TIMESTAMP, nullable)

#### `insights`
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `dataset_id` (TEXT, FOREIGN KEY)
- `insight_id` (TEXT) - Unique identifier for insight type
- `title` (TEXT)
- `category` (TEXT) - 'growth', 'risk', 'efficiency'
- `confidence` (TEXT) - 'high', 'medium', 'low'
- `supporting_metrics` (JSON) - Structured metrics
- `recommended_action` (TEXT)
- `generated_at` (TIMESTAMP)
- `is_active` (BOOLEAN) - For soft deletion

#### `ai_explanations`
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `insight_id` (INTEGER, FOREIGN KEY)
- `explanation` (TEXT) - Natural language explanation
- `guidance` (TEXT) - Business guidance
- `generated_at` (TIMESTAMP)
- `model_used` (TEXT) - 'gpt-4', 'claude-3', etc.

#### `processing_jobs`
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `job_type` (TEXT) - 'ingestion', 'analytics', 'insights'
- `dataset_id` (TEXT, nullable)
- `status` (TEXT) - 'pending', 'running', 'completed', 'failed'
- `error_message` (TEXT, nullable)
- `created_at` (TIMESTAMP)
- `started_at` (TIMESTAMP, nullable)
- `completed_at` (TIMESTAMP, nullable)

## API Endpoints

### Data Ingestion
- `POST /api/v1/datasets` - Upload new dataset
  - Body: multipart/form-data (file)
  - Response: `{dataset_id, status, row_count}`
  
- `GET /api/v1/datasets` - List all datasets
  - Query params: `status`, `source_type`
  - Response: `[{dataset_id, name, status, created_at}]`
  
- `GET /api/v1/datasets/{dataset_id}` - Get dataset details
  - Response: `{dataset_id, name, status, row_count, created_at}`
  
- `DELETE /api/v1/datasets/{dataset_id}` - Delete dataset
  - Response: `{success: true}`

### Analytics
- `GET /api/v1/analytics/{dataset_id}/best-sellers` - Best selling products
  - Query params: `limit` (default: 10), `period` (optional)
  - Response: `[{product_name, total_quantity, revenue, rank}]`
  
- `GET /api/v1/analytics/{dataset_id}/revenue-contribution` - Revenue by product
  - Query params: `limit` (default: 20)
  - Response: `[{product_name, revenue, percentage, rank}]`
  
- `GET /api/v1/analytics/{dataset_id}/seasonality` - Seasonal products
  - Query params: `min_seasonality_score` (default: 0.3)
  - Response: `[{product_name, seasonality_score, peak_months}]`
  
- `GET /api/v1/analytics/{dataset_id}/inventory-velocity` - Stock turnover
  - Response: `[{product_name, velocity_score, turnover_rate, category}]`
  
- `GET /api/v1/analytics/{dataset_id}/dead-stock` - Zero/low movement items
  - Query params: `days_threshold` (default: 90)
  - Response: `[{product_name, days_since_sale, current_stock, estimated_value}]`
  
- `GET /api/v1/analytics/{dataset_id}/profitability` - Profitability ranking
  - Response: `[{product_name, profit_margin, total_profit, rank}]`
  
- `GET /api/v1/analytics/{dataset_id}/trends` - Month-over-month trends
  - Query params: `metric` (revenue/quantity/profit), `months` (default: 6)
  - Response: `[{month, value, change_percent, trend}]`

### Insights
- `GET /api/v1/insights/{dataset_id}` - Get all insights
  - Query params: `category`, `confidence`, `limit`
  - Response: `[{insight_id, title, category, confidence, supporting_metrics, recommended_action}]`
  
- `GET /api/v1/insights/{dataset_id}/{insight_id}` - Get specific insight
  - Response: Full insight object with metrics

### AI Explanations
- `POST /api/v1/ai/explain` - Generate AI explanation
  - Body: `{dataset_id, insight_ids: []}`
  - Response: `{explanation, guidance, insights_covered: []}`
  
- `GET /api/v1/ai/explanations/{insight_id}` - Get cached explanation
  - Response: `{explanation, guidance, generated_at}`

### System
- `GET /api/v1/health` - Health check
  - Response: `{status: "healthy", version, cache_stats}`
  
- `POST /api/v1/jobs/analytics/{dataset_id}/recompute` - Force recompute
  - Response: `{job_id, status}`

## Failure & Edge Case Handling

### Data Ingestion Failures
- **Invalid file format**: Return 400 with specific error
- **Corrupted CSV**: Skip bad rows, log warnings, continue processing
- **Missing required columns**: Return 400 with column mapping suggestions
- **Empty file**: Return 400 with clear message
- **Duplicate dataset**: Detect by file hash, return existing dataset_id

### Analytics Failures
- **No data**: Return empty results with 200 status
- **Insufficient data**: Return partial results with warning flag
- **Division by zero**: Handle gracefully, return null/0
- **Cache corruption**: Auto-invalidate, recompute
- **Memory limits**: Process in chunks, stream results

### Insight Generation Failures
- **No matching rules**: Return empty insights array
- **Rule evaluation error**: Log error, skip rule, continue
- **Confidence calculation error**: Default to 'low' confidence

### AI Service Failures
- **API timeout**: Return cached explanation if available, else error
- **Rate limiting**: Queue request, retry with backoff
- **Invalid response**: Validate structure, retry once
- **No API key**: Return error with setup instructions
- **Network failure**: Return error, suggest offline mode

### General Error Handling
- **All errors**: Log with context, return structured error response
- **500 errors**: Never expose stack traces in production
- **Validation errors**: Return 422 with field-level errors
- **Not found**: Return 404 with resource identifier

## Implementation Phases

### Phase 1: Foundation
1. FastAPI setup with basic structure
2. SQLite database initialization
3. Basic ingestion (CSV only)
4. Simple analytics (best sellers)

### Phase 2: Core Analytics
1. All analytics endpoints
2. Parquet caching
3. Background job system
4. Cache invalidation

### Phase 3: Insights Engine
1. Rule system
2. Insight generation
3. Confidence scoring
4. Action recommendations

### Phase 4: AI Integration
1. AI service abstraction
2. Explanation generation
3. Response validation
4. Caching layer

### Phase 5: Polish
1. Error handling refinement
2. Performance optimization
3. Comprehensive logging
4. Documentation
