# Module Responsibilities

Detailed breakdown of each module's purpose and responsibilities.

## API Layer (`api/`)

### `api/main.py`
- FastAPI application initialization
- Middleware configuration (CORS, error handling, logging)
- Route registration
- Application lifecycle management

**Responsibilities:**
- Create FastAPI app instance
- Register all route modules
- Configure middleware
- Handle startup/shutdown events
- Global exception handlers

### `api/routes/datasets.py`
- Dataset upload and management endpoints

**Endpoints:**
- `POST /api/v1/datasets` - Upload dataset
- `GET /api/v1/datasets` - List datasets
- `GET /api/v1/datasets/{id}` - Get dataset details
- `DELETE /api/v1/datasets/{id}` - Delete dataset

**Responsibilities:**
- File upload handling
- Request validation
- Call ingestion service
- Return structured responses
- Handle upload errors

### `api/routes/analytics.py`
- Analytics computation endpoints

**Endpoints:**
- `GET /api/v1/analytics/{dataset_id}/best-sellers`
- `GET /api/v1/analytics/{dataset_id}/revenue-contribution`
- `GET /api/v1/analytics/{dataset_id}/seasonality`
- `GET /api/v1/analytics/{dataset_id}/inventory-velocity`
- `GET /api/v1/analytics/{dataset_id}/dead-stock`
- `GET /api/v1/analytics/{dataset_id}/profitability`
- `GET /api/v1/analytics/{dataset_id}/trends`

**Responsibilities:**
- Parameter validation
- Cache checking
- Call analytics engine
- Format results
- Handle empty data cases

### `api/routes/insights.py`
- Insights retrieval endpoints

**Endpoints:**
- `GET /api/v1/insights/{dataset_id}`
- `GET /api/v1/insights/{dataset_id}/{insight_id}`

**Responsibilities:**
- Filter insights by category/confidence
- Load insights from storage
- Format response
- Handle missing insights

### `api/routes/ai.py`
- AI explanation endpoints

**Endpoints:**
- `POST /api/v1/ai/explain`
- `GET /api/v1/ai/explanations/{insight_id}`

**Responsibilities:**
- Validate request payload
- Check cache for explanations
- Call AI service
- Return explanations
- Handle AI service errors

### `api/models/`
- Pydantic models for request/response validation
- Type-safe data structures
- Automatic OpenAPI schema generation

**Responsibilities:**
- Define request schemas
- Define response schemas
- Validation rules
- Serialization/deserialization

## Ingestion Service (`services/ingestion/`)

### `services/ingestion/parser.py`
- File parsing logic for different formats

**Responsibilities:**
- CSV parsing (sales, inventory, transactions)
- PDF invoice extraction (structured data)
- Vyapar export parsing
- Format detection
- Encoding handling
- Error recovery (skip bad rows)

**Key Functions:**
- `parse_csv(file_path, schema_type)` → DataFrame
- `parse_pdf(file_path)` → Structured dict
- `parse_vyapar(file_path)` → DataFrame
- `detect_format(file_path)` → 'csv' | 'pdf' | 'vyapar'

### `services/ingestion/validator.py`
- Data validation and quality checks

**Responsibilities:**
- Schema validation
- Required field checking
- Data type validation
- Range validation (negative quantities, etc.)
- Duplicate detection
- Missing value handling

**Key Functions:**
- `validate_sales_data(df)` → ValidationResult
- `validate_inventory_data(df)` → ValidationResult
- `check_duplicates(df, key_fields)` → List[duplicates]

### `services/ingestion/normalizer.py`
- Schema normalization across different sources

**Responsibilities:**
- Column name mapping
- Date format normalization
- Currency normalization
- Unit standardization
- Category mapping
- Product ID generation

**Key Functions:**
- `normalize_sales(df, source_type)` → Normalized DataFrame
- `normalize_inventory(df, source_type)` → Normalized DataFrame
- `generate_product_id(product_name, category)` → product_id

## Analytics Engine (`services/analytics/`)

### `services/analytics/best_sellers.py`
- Best selling products calculation

**Responsibilities:**
- Aggregate sales by product
- Sort by quantity or revenue
- Calculate rankings
- Handle ties
- Support time period filtering

**Key Functions:**
- `compute_best_sellers(dataset_id, limit=10, period=None)` → List[ProductSales]

### `services/analytics/revenue.py`
- Revenue contribution analysis

**Responsibilities:**
- Calculate total revenue per product
- Compute percentage contribution
- Rank products by revenue
- Support category grouping

**Key Functions:**
- `compute_revenue_contribution(dataset_id, limit=20)` → List[RevenueContribution]

### `services/analytics/seasonality.py`
- Seasonal product detection

**Responsibilities:**
- Time series analysis
- Seasonal pattern detection (statistical)
- Peak month identification
- Seasonality score calculation (0-1)
- Handle products with insufficient data

**Key Functions:**
- `detect_seasonality(dataset_id, min_score=0.3)` → List[SeasonalProduct]
- `calculate_seasonality_score(sales_by_month)` → float

### `services/analytics/inventory.py`
- Inventory velocity and turnover

**Responsibilities:**
- Calculate stock turnover rate
- Compute velocity scores
- Categorize velocity (High/Medium/Low)
- Handle missing inventory data

**Key Functions:**
- `compute_inventory_velocity(dataset_id)` → List[InventoryVelocity]
- `calculate_turnover_rate(sales_qty, avg_stock)` → float

### `services/analytics/dead_stock.py`
- Dead stock detection

**Responsibilities:**
- Identify zero-movement products
- Calculate days since last sale
- Estimate stock value
- Apply configurable thresholds

**Key Functions:**
- `detect_dead_stock(dataset_id, days_threshold=90)` → List[DeadStockItem]
- `calculate_days_since_sale(product_id, dataset_id)` → int

### `services/analytics/profitability.py`
- Profitability ranking

**Responsibilities:**
- Calculate profit margins
- Compute total profit per product
- Rank by profitability
- Handle missing cost data

**Key Functions:**
- `compute_profitability(dataset_id)` → List[ProfitabilityRanking]
- `calculate_profit_margin(revenue, cost)` → float

### `services/analytics/trends.py`
- Month-over-month trend analysis

**Responsibilities:**
- Aggregate metrics by month
- Calculate change percentages
- Identify trends (up/down/stable)
- Handle missing months
- Support multiple metrics

**Key Functions:**
- `compute_trends(dataset_id, metric='revenue', months=6)` → List[MonthlyTrend]
- `calculate_change_percent(current, previous)` → float

## Insights Engine (`services/insights/`)

### `services/insights/engine.py`
- Main insight generation orchestrator

**Responsibilities:**
- Load analytics data
- Evaluate all rules
- Generate insights
- Score confidence
- Attach supporting metrics
- Store insights

**Key Functions:**
- `generate_insights(dataset_id)` → List[Insight]
- `evaluate_rules(analytics_data)` → List[RuleResult]

### `services/insights/rules/growth_rules.py`
- Growth opportunity rules

**Example Rules:**
- High-velocity low-stock products → "Growth: Restock opportunity"
- Seasonal products approaching peak → "Growth: Prepare for demand spike"
- Top sellers with increasing trend → "Growth: Scale inventory"

**Responsibilities:**
- Define growth rules
- Evaluate conditions
- Generate insight titles
- Suggest actions

### `services/insights/rules/risk_rules.py`
- Risk identification rules

**Example Rules:**
- Dead stock detection → "Risk: Dead stock identified"
- Declining trends → "Risk: Sales declining"
- High inventory low velocity → "Risk: Overstock risk"

**Responsibilities:**
- Define risk rules
- Evaluate conditions
- Generate insight titles
- Suggest actions

### `services/insights/rules/efficiency_rules.py`
- Efficiency optimization rules

**Example Rules:**
- Low-margin high-volume → "Efficiency: Optimize pricing"
- High inventory costs → "Efficiency: Reduce stock levels"
- Slow-moving categories → "Efficiency: Review category strategy"

**Responsibilities:**
- Define efficiency rules
- Evaluate conditions
- Generate insight titles
- Suggest actions

### `services/insights/scorer.py`
- Confidence scoring logic

**Responsibilities:**
- Calculate confidence based on:
  - Data completeness
  - Statistical significance
  - Rule match strength
  - Historical accuracy
- Assign high/medium/low confidence

**Key Functions:**
- `score_confidence(rule_result, data_quality)` → 'high' | 'medium' | 'low'

## AI Service (`services/ai/`)

### `services/ai/client.py`
- AI provider abstraction layer

**Responsibilities:**
- Abstract OpenAI/Claude differences
- Handle API calls
- Retry logic
- Rate limiting
- Error handling
- Response parsing

**Key Functions:**
- `generate_explanation(context)` → Explanation
- `validate_api_key()` → bool

### `services/ai/prompt.py`
- Prompt construction for AI

**Responsibilities:**
- Build structured prompts
- Include business context
- Include computed metrics
- Include generated insights
- Format for model consumption
- Ensure no raw data leakage

**Key Functions:**
- `build_explanation_prompt(insights, metrics, context)` → str
- `build_guidance_prompt(insights, metrics)` → str

### `services/ai/validator.py`
- AI response validation

**Responsibilities:**
- Validate response structure
- Check for invented numbers
- Ensure all claims backed by metrics
- Detect hallucinations
- Extract structured data

**Key Functions:**
- `validate_explanation(response, insights)` → ValidationResult
- `check_for_invented_metrics(response, available_metrics)` → bool

## Storage Layer (`storage/`)

### `storage/database.py`
- SQLite database operations

**Responsibilities:**
- Connection management
- Query execution
- Transaction handling
- Error handling
- Connection pooling

**Key Functions:**
- `execute_query(query, params)` → List[Row]
- `execute_transaction(queries)` → bool
- `get_connection()` → Connection

### `storage/cache.py`
- Parquet cache management

**Responsibilities:**
- Write analytics to Parquet
- Read cached analytics
- Cache invalidation
- Cache expiration
- File management

**Key Functions:**
- `write_cache(dataset_id, cache_key, data)` → str (path)
- `read_cache(dataset_id, cache_key)` → DataFrame | None
- `invalidate_cache(dataset_id, cache_key=None)` → bool
- `is_cache_valid(dataset_id, cache_key)` → bool

## Background Jobs (`jobs/`)

### `jobs/queue.py`
- Job queue management

**Responsibilities:**
- Queue job creation
- Job status tracking
- Priority handling
- Retry logic
- Job cancellation

**Key Functions:**
- `enqueue_job(job_type, dataset_id, priority='normal')` → job_id
- `get_job_status(job_id)` → JobStatus
- `cancel_job(job_id)` → bool

### `jobs/workers.py`
- Background job workers

**Responsibilities:**
- Process queued jobs
- Handle job failures
- Update job status
- Log progress
- Timeout handling

**Key Functions:**
- `process_ingestion_job(job_id)` → None
- `process_analytics_job(job_id)` → None
- `process_insights_job(job_id)` → None

### `jobs/tasks.py`
- Job task definitions

**Responsibilities:**
- Define job tasks
- Task dependencies
- Task parameters
- Error handling per task

## Utilities (`utils/`)

### `utils/hashing.py`
- File and data hashing

**Responsibilities:**
- SHA256 file hashing
- Data hash computation
- Hash comparison
- Change detection

**Key Functions:**
- `hash_file(file_path)` → str (SHA256)
- `hash_data(data)` → str (SHA256)

### `utils/logging.py`
- Logging configuration

**Responsibilities:**
- Logger setup
- Log levels
- File rotation
- Structured logging

### `utils/exceptions.py`
- Custom exception classes

**Exception Types:**
- `IngestionError`
- `AnalyticsError`
- `InsightError`
- `AIServiceError`
- `CacheError`
- `DatabaseError`
