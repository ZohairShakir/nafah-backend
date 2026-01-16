# Complete Folder Structure

```
backend/
│
├── api/                          # FastAPI Application Layer
│   ├── __init__.py
│   ├── main.py                  # FastAPI app initialization
│   │
│   ├── routes/                   # API Route Handlers
│   │   ├── __init__.py
│   │   ├── datasets.py          # Dataset CRUD endpoints
│   │   ├── analytics.py         # Analytics endpoints
│   │   ├── insights.py          # Insights endpoints
│   │   ├── ai.py                # AI explanation endpoints
│   │   └── system.py            # Health check, system endpoints
│   │
│   └── models/                   # Pydantic Request/Response Models
│       ├── __init__.py
│       ├── datasets.py          # Dataset models
│       ├── analytics.py         # Analytics models
│       ├── insights.py          # Insight models
│       └── common.py            # Shared models (errors, pagination)
│
├── services/                     # Business Logic Layer
│   ├── __init__.py
│   │
│   ├── ingestion/               # Data Ingestion Service
│   │   ├── __init__.py
│   │   ├── parser.py            # CSV/PDF/Vyapar parsers
│   │   ├── validator.py         # Data validation
│   │   ├── normalizer.py        # Schema normalization
│   │   └── schemas.py           # Data schemas
│   │
│   ├── analytics/               # Analytics Computation Engine
│   │   ├── __init__.py
│   │   ├── best_sellers.py      # Best selling products
│   │   ├── revenue.py           # Revenue contribution
│   │   ├── seasonality.py      # Seasonal product detection
│   │   ├── inventory.py         # Inventory velocity
│   │   ├── dead_stock.py        # Dead stock detection
│   │   ├── profitability.py     # Profitability ranking
│   │   ├── trends.py            # Month-over-month trends
│   │   └── engine.py            # Analytics orchestrator
│   │
│   ├── insights/                # Rule-Based Insights Engine
│   │   ├── __init__.py
│   │   ├── engine.py           # Main insight engine
│   │   ├── scorer.py           # Confidence scoring
│   │   │
│   │   └── rules/              # Insight Rules
│   │       ├── __init__.py
│   │       ├── base.py        # Base rule class
│   │       ├── growth_rules.py    # Growth opportunity rules
│   │       ├── risk_rules.py      # Risk identification rules
│   │       └── efficiency_rules.py # Efficiency optimization rules
│   │
│   └── ai/                     # AI Explanation Service
│       ├── __init__.py
│       ├── client.py           # AI provider abstraction (OpenAI/Claude)
│       ├── prompt.py           # Prompt construction
│       ├── validator.py        # Response validation
│       └── providers/          # Provider implementations
│           ├── __init__.py
│           ├── openai.py       # OpenAI implementation
│           └── claude.py       # Claude implementation
│
├── storage/                     # Data Persistence Layer
│   ├── __init__.py
│   ├── database.py             # SQLite operations
│   ├── cache.py                # Parquet cache manager
│   ├── models.py               # SQLAlchemy ORM models (optional)
│   └── migrations/             # Database migrations (future)
│       └── __init__.py
│
├── jobs/                        # Background Job Processing
│   ├── __init__.py
│   ├── queue.py                # Job queue manager
│   ├── workers.py              # Job workers
│   ├── tasks.py                # Job task definitions
│   └── scheduler.py            # Job scheduler (optional)
│
├── utils/                       # Shared Utilities
│   ├── __init__.py
│   ├── hashing.py              # File/data hashing (SHA256)
│   ├── logging.py              # Logging configuration
│   ├── exceptions.py           # Custom exception classes
│   ├── validators.py           # Common validators
│   └── helpers.py              # Helper functions
│
├── scripts/                     # Utility Scripts
│   ├── __init__.py
│   ├── init_db.py              # Database initialization
│   ├── migrate.py              # Database migrations
│   └── seed_data.py            # Seed test data (dev)
│
├── tests/                       # Test Suite
│   ├── __init__.py
│   ├── conftest.py             # Pytest configuration
│   │
│   ├── unit/                   # Unit Tests
│   │   ├── __init__.py
│   │   ├── test_ingestion.py
│   │   ├── test_analytics.py
│   │   ├── test_insights.py
│   │   └── test_ai.py
│   │
│   ├── integration/            # Integration Tests
│   │   ├── __init__.py
│   │   ├── test_api.py
│   │   ├── test_database.py
│   │   └── test_cache.py
│   │
│   └── fixtures/               # Test Fixtures
│       ├── __init__.py
│       ├── sample_data.py      # Sample CSV/Data
│       └── mocks.py            # Mock objects
│
├── data/                       # Data Directory (gitignored)
│   ├── lucid.db               # SQLite database
│   ├── parquet/               # Parquet cache files
│   │   └── {dataset_id}_{cache_key}.parquet
│   └── uploads/               # Uploaded files (optional)
│       └── {dataset_id}_{filename}
│
├── logs/                       # Log Files (gitignored)
│   └── lucid.log
│
├── .env                        # Environment Variables (gitignored)
├── .env.example                # Example environment file
├── .gitignore                  # Git ignore rules
│
├── requirements.txt            # Python dependencies
├── requirements-dev.txt        # Dev dependencies (optional)
│
├── README.md                   # Quick start guide
├── ARCHITECTURE.md             # System architecture
├── DATABASE_SCHEMA.sql         # Database schema
├── MODULE_RESPONSIBILITIES.md  # Module breakdown
├── DATA_PIPELINES.md           # Pipeline flows
├── IMPLEMENTATION_GUIDE.md     # Implementation steps
├── DESIGN_SUMMARY.md           # Design overview
├── FOLDER_STRUCTURE.md         # This file
│
└── api/
    └── endpoints.md            # API endpoint documentation
```

## Key Directories Explained

### `api/`
FastAPI application layer. Handles HTTP requests, validation, and responses.

### `services/`
Core business logic. Organized by domain (ingestion, analytics, insights, AI).

### `storage/`
Data persistence. SQLite for metadata, Parquet for analytics cache.

### `jobs/`
Background processing. Async job queue for heavy computations.

### `utils/`
Shared utilities used across modules.

### `scripts/`
One-off scripts for setup, migrations, seeding.

### `tests/`
Comprehensive test suite (unit + integration).

### `data/`
Runtime data (database, cache, uploads). Gitignored.

## File Naming Conventions

- **Modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_leading_underscore`

## Import Structure

```python
# Standard library
import os
from typing import List, Dict

# Third-party
import pandas as pd
from fastapi import APIRouter

# Local imports
from services.analytics import best_sellers
from storage.database import Database
from utils.exceptions import IngestionError
```

## Module Dependencies

```
api/
  └── depends on ──► services/
                      └── depends on ──► storage/
                                           └── depends on ──► utils/
```

**No circular dependencies allowed.**

## Data Flow Through Structure

```
Request → api/routes/ → api/models/ (validation)
           ↓
        services/ (business logic)
           ↓
        storage/ (persistence)
           ↓
        Response ← api/routes/
```
