# Implementation Guide

Step-by-step guide for implementing the Lucid backend.

## Phase 1: Foundation (Week 1)

### 1.1 Project Setup
```bash
mkdir backend
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### 1.2 Database Initialization
```python
# scripts/init_db.py
import sqlite3
from pathlib import Path

def init_database(db_path: str = "data/lucid.db"):
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    with open("DATABASE_SCHEMA.sql", "r") as f:
        conn.executescript(f.read())
    conn.close()
    print(f"Database initialized at {db_path}")
```

### 1.3 Basic FastAPI App
```python
# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Lucid Backend API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for Tauri
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}
```

### 1.4 Basic CSV Ingestion
```python
# services/ingestion/parser.py
import pandas as pd
from typing import Dict, Any

def parse_csv(file_path: str, schema_type: str = "sales") -> pd.DataFrame:
    """Parse CSV file based on schema type."""
    df = pd.read_csv(file_path, on_bad_lines='skip')
    
    # Basic validation
    if len(df) == 0:
        raise ValueError("CSV file is empty")
    
    return df
```

**Deliverables:**
- ✅ FastAPI app running
- ✅ Database initialized
- ✅ Basic CSV upload endpoint
- ✅ Health check endpoint

---

## Phase 2: Core Analytics (Week 2-3)

### 2.1 Data Storage Layer
```python
# storage/database.py
import aiosqlite
from typing import List, Dict, Any

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
```

### 2.2 Analytics Engine - Best Sellers
```python
# services/analytics/best_sellers.py
import pandas as pd
from storage.database import Database

async def compute_best_sellers(
    db: Database,
    dataset_id: str,
    limit: int = 10
) -> List[Dict]:
    # Load sales data
    query = """
        SELECT product_name, product_id, quantity, total_amount, category
        FROM raw_sales
        WHERE dataset_id = ?
    """
    rows = await db.execute_query(query, (dataset_id,))
    df = pd.DataFrame(rows)
    
    # Aggregate
    aggregated = df.groupby(['product_name', 'product_id', 'category']).agg({
        'quantity': 'sum',
        'total_amount': 'sum'
    }).reset_index()
    
    # Sort and rank
    aggregated = aggregated.sort_values('quantity', ascending=False)
    aggregated['rank'] = range(1, len(aggregated) + 1)
    
    # Return top N
    return aggregated.head(limit).to_dict('records')
```

### 2.3 Cache Layer
```python
# storage/cache.py
import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from datetime import datetime, timedelta

class CacheManager:
    def __init__(self, cache_dir: str = "data/parquet"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_path(self, dataset_id: str, cache_key: str) -> Path:
        return self.cache_dir / f"{dataset_id}_{cache_key}.parquet"
    
    def write(self, dataset_id: str, cache_key: str, df: pd.DataFrame):
        path = self.get_cache_path(dataset_id, cache_key)
        df.to_parquet(path, index=False)
    
    def read(self, dataset_id: str, cache_key: str) -> pd.DataFrame | None:
        path = self.get_cache_path(dataset_id, cache_key)
        if path.exists():
            return pd.read_parquet(path)
        return None
```

### 2.4 Analytics Endpoints
```python
# api/routes/analytics.py
from fastapi import APIRouter, HTTPException
from services.analytics import best_sellers
from storage.cache import CacheManager

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

@router.get("/{dataset_id}/best-sellers")
async def get_best_sellers(
    dataset_id: str,
    limit: int = 10
):
    cache = CacheManager()
    
    # Check cache
    cached = cache.read(dataset_id, "best_sellers")
    if cached is not None:
        return {"results": cached.to_dict('records'), "cached": True}
    
    # Compute
    db = Database()
    results = await best_sellers.compute_best_sellers(db, dataset_id, limit)
    
    # Cache
    cache.write(dataset_id, "best_sellers", pd.DataFrame(results))
    
    return {"results": results, "cached": False}
```

**Deliverables:**
- ✅ All analytics endpoints implemented
- ✅ Parquet caching working
- ✅ Cache invalidation on data change
- ✅ Error handling

---

## Phase 3: Insights Engine (Week 4)

### 3.1 Rule System
```python
# services/insights/rules/risk_rules.py
from typing import List, Dict

def evaluate_dead_stock_rule(dead_stock_data: List[Dict]) -> List[Dict]:
    insights = []
    
    for item in dead_stock_data:
        if item['days_since_sale'] > 90 and item['current_stock'] > 0:
            insights.append({
                'insight_id': f"dead_stock_{item['product_id']}",
                'title': f"Dead Stock: {item['product_name']}",
                'category': 'risk',
                'confidence': 'high' if item['days_since_sale'] > 180 else 'medium',
                'supporting_metrics': {
                    'days_since_sale': item['days_since_sale'],
                    'current_stock': item['current_stock'],
                    'estimated_value': item['estimated_value']
                },
                'recommended_action': (
                    f"Consider discounting or discontinuing {item['product_name']}. "
                    f"Stock value: ₹{item['estimated_value']}"
                )
            })
    
    return insights
```

### 3.2 Insights Engine
```python
# services/insights/engine.py
from services.analytics import dead_stock, seasonality
from services.insights.rules import risk_rules, growth_rules

async def generate_insights(db: Database, dataset_id: str) -> List[Dict]:
    # Load analytics
    dead_stock_data = await dead_stock.compute(db, dataset_id)
    seasonal_data = await seasonality.compute(db, dataset_id)
    
    insights = []
    
    # Evaluate rules
    insights.extend(risk_rules.evaluate_dead_stock_rule(dead_stock_data))
    insights.extend(growth_rules.evaluate_seasonal_peak_rule(seasonal_data))
    
    # Store insights
    for insight in insights:
        await db.execute_query(
            """INSERT INTO insights 
               (dataset_id, insight_id, title, category, confidence, 
                supporting_metrics, recommended_action)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (dataset_id, insight['insight_id'], insight['title'],
             insight['category'], insight['confidence'],
             json.dumps(insight['supporting_metrics']),
             insight['recommended_action'])
        )
    
    return insights
```

**Deliverables:**
- ✅ Rule system implemented
- ✅ Insight generation working
- ✅ Confidence scoring
- ✅ Insights endpoints

---

## Phase 4: AI Integration (Week 5)

### 4.1 AI Client Abstraction
```python
# services/ai/client.py
from openai import OpenAI
from typing import Dict, Optional
import os

class AIClient:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("AI_MODEL", "gpt-4")
    
    async def generate_explanation(
        self,
        context: Dict
    ) -> Dict[str, str]:
        prompt = self._build_prompt(context)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a business analyst..."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        explanation = response.choices[0].message.content
        
        # Validate response
        if not self._validate_response(explanation, context):
            raise ValueError("AI response validation failed")
        
        return {
            "explanation": explanation,
            "guidance": self._extract_guidance(explanation)
        }
```

### 4.2 AI Service Integration
```python
# api/routes/ai.py
from fastapi import APIRouter, HTTPException
from services.ai.client import AIClient
from services.insights.engine import get_insights

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

@router.post("/explain")
async def generate_explanation(request: ExplainRequest):
    # Load insights
    insights = await get_insights(request.dataset_id)
    
    # Build context (NO RAW DATA)
    context = {
        "business_context": {...},
        "computed_metrics": {...},
        "generated_insights": insights
    }
    
    # Generate explanation
    ai_client = AIClient()
    try:
        result = await ai_client.generate_explanation(context)
        return result
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
```

**Deliverables:**
- ✅ AI service integrated
- ✅ Explanation generation
- ✅ Response validation
- ✅ Caching

---

## Phase 5: Background Jobs (Week 6)

### 5.1 Simple Job Queue
```python
# jobs/queue.py
import asyncio
from typing import Dict, Optional
from datetime import datetime

class JobQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.jobs = {}  # job_id -> job_data
    
    async def enqueue(self, job_type: str, dataset_id: str, params: Dict = None):
        job_id = len(self.jobs) + 1
        job = {
            "id": job_id,
            "type": job_type,
            "dataset_id": dataset_id,
            "params": params or {},
            "status": "pending",
            "created_at": datetime.now()
        }
        self.jobs[job_id] = job
        await self.queue.put(job_id)
        return job_id
    
    async def process_next(self):
        job_id = await self.queue.get()
        job = self.jobs[job_id]
        job["status"] = "running"
        # Process job...
        job["status"] = "completed"
```

### 5.2 Worker Implementation
```python
# jobs/workers.py
import asyncio
from jobs.queue import JobQueue
from services.analytics import compute_all

async def worker_loop(queue: JobQueue):
    while True:
        try:
            job_id = await queue.process_next()
            job = queue.jobs[job_id]
            
            if job["type"] == "analytics":
                await compute_all(job["dataset_id"])
            
            job["status"] = "completed"
        except Exception as e:
            job["status"] = "failed"
            job["error"] = str(e)
        
        await asyncio.sleep(1)
```

**Deliverables:**
- ✅ Background job system
- ✅ Async processing
- ✅ Job status tracking

---

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_analytics.py
import pytest
from services.analytics import best_sellers

def test_best_sellers_computation():
    # Mock data
    sales_data = [...]
    result = best_sellers.compute(sales_data, limit=5)
    assert len(result) == 5
    assert result[0]['rank'] == 1
```

### Integration Tests
```python
# tests/integration/test_api.py
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_upload_dataset():
    response = client.post("/api/v1/datasets", files={"file": ...})
    assert response.status_code == 200
    assert "dataset_id" in response.json()
```

---

## Deployment Checklist

- [ ] Environment variables configured
- [ ] Database initialized
- [ ] Cache directory created
- [ ] AI API keys set
- [ ] Logging configured
- [ ] Error handling tested
- [ ] Performance tested
- [ ] Security reviewed
- [ ] Documentation complete

---

## Performance Optimization

1. **Database Indexing**: All foreign keys and frequently queried columns indexed
2. **Parquet Caching**: Analytics cached until source data changes
3. **Batch Processing**: Process large datasets in chunks
4. **Connection Pooling**: Reuse database connections
5. **Lazy Loading**: Load data only when needed

---

## Security Considerations

1. **File Upload Limits**: Max file size (100MB)
2. **Input Validation**: All inputs validated
3. **SQL Injection**: Use parameterized queries
4. **Path Traversal**: Validate file paths
5. **API Keys**: Store securely, never commit

---

## Next Steps After Implementation

1. Add authentication if needed
2. Implement data export features
3. Add more analytics types
4. Enhance AI prompts
5. Add data visualization endpoints
6. Implement real-time updates (WebSockets)
