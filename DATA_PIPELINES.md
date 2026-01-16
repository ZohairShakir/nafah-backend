# Data Pipelines & Flow Diagrams

Detailed flow diagrams and logic for each pipeline.

## 1. Data Ingestion Pipeline

### Flow Diagram
```
┌─────────────┐
│ File Upload │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Validate File   │ ◄─── File exists? Size > 0? Format supported?
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Compute Hash    │ ◄─── SHA256(file_content)
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│ Check Duplicate │ ◄─── SELECT * FROM datasets WHERE file_hash = ?
└──────┬──────────┘
       │
       ├─── YES ──► Return existing dataset_id
       │
       └─── NO ──►
                  │
                  ▼
         ┌─────────────────┐
         │ Create Dataset  │ ◄─── INSERT INTO datasets (status='pending')
         └────────┬─────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ Detect Format  │ ◄─── Check extension, header, content
         └────────┬─────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ Parse File      │ ◄─── CSV/PDF/Vyapar parser
         └────────┬─────────┘
                  │
                  ▼
         ┌─────────────────┐
         │ Validate Data   │ ◄─── Schema, types, ranges, duplicates
         └────────┬─────────┘
                  │
                  ├─── FAIL ──► Update status='error', return error
                  │
                  └─── PASS ──►
                             │
                             ▼
                   ┌─────────────────┐
                   │ Normalize Schema│ ◄─── Map columns, standardize formats
                   └────────┬─────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Store Raw Data  │ ◄─── INSERT INTO raw_sales/raw_inventory
                   └────────┬─────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Update Dataset  │ ◄─── status='completed', row_count
                   └────────┬─────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Invalidate Cache│ ◄─── DELETE FROM analytics_cache WHERE dataset_id=?
                   └────────┬─────────┘
                            │
                            ▼
                   ┌─────────────┐
                   │ Return Success│
                   └─────────────┘
```

### Error Handling

**Invalid File Format**
```python
try:
    parser = detect_parser(file_path)
except UnsupportedFormatError:
    return {
        "error": "unsupported_format",
        "message": f"Format not supported. Supported: CSV, PDF, Vyapar",
        "status_code": 400
    }
```

**Corrupted CSV**
```python
try:
    df = pd.read_csv(file_path, on_bad_lines='skip')
    if len(df) == 0:
        raise EmptyFileError()
except pd.errors.EmptyDataError:
    return {"error": "empty_file", "status_code": 400}
except Exception as e:
    # Log bad rows, continue with valid rows
    logger.warning(f"Skipped {bad_row_count} invalid rows")
    # Continue processing
```

**Missing Required Columns**
```python
required_columns = ['date', 'product_name', 'quantity', 'unit_price']
missing = set(required_columns) - set(df.columns)
if missing:
    return {
        "error": "missing_columns",
        "missing": list(missing),
        "suggestions": suggest_column_mapping(df.columns, required_columns),
        "status_code": 400
    }
```

## 2. Analytics Computation Pipeline

### Flow Diagram
```
┌──────────────────────┐
│ Request Analytics    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Check Cache          │ ◄─── SELECT * FROM analytics_cache WHERE dataset_id=? AND cache_key=?
└──────────┬───────────┘
           │
           ├─── VALID ──► Read Parquet → Return Results
           │
           └─── INVALID/MISSING ──►
                      │
                      ▼
            ┌──────────────────────┐
            │ Load Raw Data        │ ◄─── SELECT * FROM raw_sales WHERE dataset_id=?
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Check Data Quality   │ ◄─── Row count > 0? Required fields present?
            └──────────┬───────────┘
                       │
                       ├─── INSUFFICIENT ──► Return empty result with warning
                       │
                       └─── SUFFICIENT ──►
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │ Compute Analytics    │ ◄─── Analytics-specific computation
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │ Validate Results     │ ◄─── Check for NaN, infinities, negative values
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │ Write to Parquet     │ ◄─── Write DataFrame to Parquet
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │ Update Cache Metadata│ ◄─── INSERT INTO analytics_cache
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │ Return Results       │
                       └──────────────────────┘
```

### Cache Validation Logic

```python
def is_cache_valid(dataset_id: str, cache_key: str) -> bool:
    # Get cache entry
    cache_entry = db.get_cache_entry(dataset_id, cache_key)
    if not cache_entry:
        return False
    
    # Check expiration
    if cache_entry.expires_at and cache_entry.expires_at < now():
        return False
    
    # Check if source data changed
    dataset = db.get_dataset(dataset_id)
    if dataset.file_hash != cache_entry.data_hash:
        return False
    
    # Check if Parquet file exists
    if not os.path.exists(cache_entry.parquet_path):
        return False
    
    return True
```

### Analytics Computation Examples

**Best Sellers**
```python
def compute_best_sellers(dataset_id: str, limit: int = 10):
    # Load sales data
    df = load_sales_data(dataset_id)
    
    # Aggregate by product
    aggregated = df.groupby('product_name').agg({
        'quantity': 'sum',
        'total_amount': 'sum'
    }).reset_index()
    
    # Sort and rank
    aggregated = aggregated.sort_values('quantity', ascending=False)
    aggregated['rank'] = range(1, len(aggregated) + 1)
    
    # Limit results
    return aggregated.head(limit).to_dict('records')
```

**Seasonality Detection**
```python
def detect_seasonality(dataset_id: str, min_score: float = 0.3):
    # Load sales data
    df = load_sales_data(dataset_id)
    
    # Group by product and month
    monthly_sales = df.groupby(['product_name', df['date'].dt.month])['quantity'].sum()
    
    results = []
    for product in df['product_name'].unique():
        product_monthly = monthly_sales[product]
        
        # Calculate coefficient of variation
        if len(product_monthly) < 6:  # Need at least 6 months
            continue
        
        cv = product_monthly.std() / product_monthly.mean()
        
        # Identify peak months (top 2 months)
        peak_months = product_monthly.nlargest(2).index.tolist()
        
        # Seasonality score (0-1)
        score = min(cv / 0.5, 1.0)  # Normalize
        
        if score >= min_score:
            results.append({
                'product_name': product,
                'seasonality_score': score,
                'peak_months': peak_months
            })
    
    return results
```

## 3. Insights Generation Pipeline

### Flow Diagram
```
┌──────────────────────┐
│ Request Insights     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Load Analytics Data  │ ◄─── Load all required analytics
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Load Existing        │ ◄─── Check if insights already generated
│ Insights (Optional)  │
└──────────┬───────────┘
           │
           ├─── EXISTS & VALID ──► Return existing insights
           │
           └─── MISSING/INVALID ──►
                      │
                      ▼
            ┌──────────────────────┐
            │ Evaluate Rules       │ ◄─── Loop through all rules
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Rule: Dead Stock?   │
            └──────────┬───────────┘
                       │
                       ├─── MATCH ──► Generate insight
                       │
                       └─── NO MATCH ──► Skip
                       │
                       ▼
            ┌──────────────────────┐
            │ Rule: Seasonal Peak? │
            └──────────┬───────────┘
                       │
                       ├─── MATCH ──► Generate insight
                       │
                       └─── NO MATCH ──► Skip
                       │
                       ▼
            ┌──────────────────────┐
            │ ... (More Rules)     │
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Score Confidence     │ ◄─── Based on data quality, rule strength
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Attach Metrics       │ ◄─── Include supporting analytics data
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Generate Actions    │ ◄─── Rule-specific recommendations
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Store Insights      │ ◄─── INSERT INTO insights
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Return Insights      │
            └──────────────────────┘
```

### Rule Evaluation Example

```python
def evaluate_dead_stock_rule(analytics_data: dict) -> List[Insight]:
    insights = []
    
    # Get dead stock analytics
    dead_stock = analytics_data.get('dead_stock', [])
    
    for item in dead_stock:
        if item['days_since_sale'] > 90 and item['current_stock'] > 0:
            insight = {
                'insight_id': f"dead_stock_{item['product_id']}",
                'title': f"Dead Stock: {item['product_name']}",
                'category': 'risk',
                'confidence': score_confidence(item),
                'supporting_metrics': {
                    'days_since_sale': item['days_since_sale'],
                    'current_stock': item['current_stock'],
                    'estimated_value': item['estimated_value']
                },
                'recommended_action': f"Consider discounting or discontinuing {item['product_name']}. Stock value: ₹{item['estimated_value']}"
            }
            insights.append(insight)
    
    return insights
```

### Confidence Scoring

```python
def score_confidence(rule_result: dict, data_quality: dict) -> str:
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
```

## 4. AI Explanation Pipeline

### Flow Diagram
```
┌──────────────────────┐
│ Request Explanation  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Load Insights        │ ◄─── SELECT * FROM insights WHERE dataset_id=?
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Load Analytics       │ ◄─── Load relevant metrics
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Check Cache          │ ◄─── SELECT * FROM ai_explanations WHERE insight_id=?
└──────────┬───────────┘
           │
           ├─── EXISTS ──► Return cached explanation
           │
           └─── MISSING ──►
                      │
                      ▼
            ┌──────────────────────┐
            │ Build Context        │ ◄─── NO RAW DATA, only structured summaries
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Construct Prompt     │ ◄─── Include insights + metrics + business context
            └──────────┬───────────┘
                       │
                       ▼
            ┌──────────────────────┐
            │ Call AI Service     │ ◄─── OpenAI/Claude API
            └──────────┬───────────┘
                       │
                       ├─── ERROR ──► Return error, log
                       │
                       └─── SUCCESS ──►
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │ Validate Response    │ ◄─── Check for invented numbers, hallucinations
                       └──────────┬───────────┘
                                  │
                                  ├─── INVALID ──► Retry once, then return error
                                  │
                                  └─── VALID ──►
                                             │
                                             ▼
                                  ┌──────────────────────┐
                                  │ Extract Explanation  │ ◄─── Parse structured response
                                  └──────────┬───────────┘
                                             │
                                             ▼
                                  ┌──────────────────────┐
                                  │ Cache Explanation    │ ◄─── INSERT INTO ai_explanations
                                  └──────────┬───────────┘
                                             │
                                             ▼
                                  ┌──────────────────────┐
                                  │ Return Explanation   │
                                  └──────────────────────┘
```

### Context Building (No Raw Data)

```python
def build_ai_context(dataset_id: str, insight_ids: List[int]) -> dict:
    # Load insights (structured)
    insights = db.get_insights(insight_ids)
    
    # Load relevant metrics (aggregated only)
    analytics = {
        'total_revenue': analytics_service.get_total_revenue(dataset_id),
        'top_products': analytics_service.get_best_sellers(dataset_id, limit=5),
        'dead_stock_count': len(analytics_service.get_dead_stock(dataset_id)),
        'seasonal_products': analytics_service.get_seasonal_products(dataset_id)
    }
    
    # Business context (metadata only)
    dataset = db.get_dataset(dataset_id)
    context = {
        'business_type': 'kirana_store',  # From config
        'dataset_period': f"{dataset.created_at} to {dataset.updated_at}",
        'total_products': dataset.row_count
    }
    
    return {
        'business_context': context,
        'computed_metrics': analytics,
        'generated_insights': [
            {
                'title': i.title,
                'category': i.category,
                'confidence': i.confidence,
                'supporting_metrics': json.loads(i.supporting_metrics),
                'recommended_action': i.recommended_action
            }
            for i in insights
        ]
    }
```

### Prompt Construction

```python
def build_explanation_prompt(context: dict) -> str:
    prompt = f"""You are a business analyst assistant for a small retail business.

Business Context:
- Type: {context['business_context']['business_type']}
- Analysis Period: {context['business_context']['dataset_period']}
- Total Products Tracked: {context['business_context']['total_products']}

Computed Metrics:
- Total Revenue: ₹{context['computed_metrics']['total_revenue']}
- Top Products: {', '.join([p['product_name'] for p in context['computed_metrics']['top_products']])}
- Dead Stock Items: {context['computed_metrics']['dead_stock_count']}
- Seasonal Products: {len(context['computed_metrics']['seasonal_products'])}

Generated Insights:
"""
    
    for insight in context['generated_insights']:
        prompt += f"""
- {insight['title']} ({insight['category']}, {insight['confidence']} confidence)
  Supporting Metrics: {insight['supporting_metrics']}
  Recommended Action: {insight['recommended_action']}
"""
    
    prompt += """
Please provide:
1. A natural language explanation of these insights
2. Business guidance based on these insights

IMPORTANT:
- Only reference metrics provided above
- Do not invent any numbers
- All advice must be backed by the provided metrics
- Keep explanations concise and actionable
"""
    
    return prompt
```

### Response Validation

```python
def validate_explanation(response: str, available_metrics: dict) -> ValidationResult:
    # Extract all numbers from response
    numbers = re.findall(r'\d+\.?\d*', response)
    
    # Check if any numbers don't match available metrics
    for num in numbers:
        if not is_number_in_metrics(float(num), available_metrics):
            return ValidationResult(
                valid=False,
                error=f"Found invented number: {num}",
                suggestion="Regenerate explanation without inventing metrics"
            )
    
    # Check for required sections
    if 'explanation' not in response.lower():
        return ValidationResult(valid=False, error="Missing explanation section")
    
    return ValidationResult(valid=True)
```

## 5. Background Job Processing

### Job Queue Flow

```python
# Job creation
job_id = queue.enqueue_job(
    job_type='analytics',
    dataset_id='abc123',
    priority='normal',
    params={'analytics_type': 'best_sellers'}
)

# Worker picks up job
def worker_loop():
    while True:
        job = queue.get_next_job()
        if job:
            process_job(job)
        else:
            sleep(1)

# Job processing
def process_job(job):
    db.update_job_status(job.id, 'running', started_at=now())
    
    try:
        if job.job_type == 'analytics':
            analytics_service.compute(job.dataset_id, job.params)
        elif job.job_type == 'insights':
            insights_service.generate(job.dataset_id)
        
        db.update_job_status(job.id, 'completed', completed_at=now())
    except Exception as e:
        db.update_job_status(job.id, 'failed', error_message=str(e))
        logger.error(f"Job {job.id} failed: {e}")
```
