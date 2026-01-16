# Lucid Backend

Local-first analytics backend for Lucid desktop application.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Run development server
uvicorn api.main:app --reload --port 8000
```

## Project Structure

```
backend/
├── api/                    # FastAPI application layer
│   ├── main.py            # FastAPI app initialization
│   ├── routes/            # API route handlers
│   │   ├── datasets.py
│   │   ├── analytics.py
│   │   ├── insights.py
│   │   └── ai.py
│   └── models/            # Pydantic request/response models
│       ├── datasets.py
│       ├── analytics.py
│       └── insights.py
│
├── services/              # Business logic layer
│   ├── ingestion/        # Data ingestion service
│   │   ├── __init__.py
│   │   ├── parser.py     # File parsers (CSV, PDF, Vyapar)
│   │   ├── validator.py  # Data validation
│   │   └── normalizer.py # Schema normalization
│   │
│   ├── analytics/        # Analytics computation engine
│   │   ├── __init__.py
│   │   ├── best_sellers.py
│   │   ├── revenue.py
│   │   ├── seasonality.py
│   │   ├── inventory.py
│   │   ├── profitability.py
│   │   └── trends.py
│   │
│   ├── insights/         # Rule-based insights engine
│   │   ├── __init__.py
│   │   ├── engine.py    # Main insight engine
│   │   ├── rules/        # Insight rules
│   │   │   ├── growth_rules.py
│   │   │   ├── risk_rules.py
│   │   │   └── efficiency_rules.py
│   │   └── scorer.py    # Confidence scoring
│   │
│   └── ai/              # AI explanation service
│       ├── __init__.py
│       ├── client.py    # AI provider abstraction
│       ├── prompt.py    # Prompt construction
│       └── validator.py # Response validation
│
├── storage/             # Data persistence layer
│   ├── __init__.py
│   ├── database.py      # SQLite operations
│   ├── cache.py         # Parquet cache manager
│   └── models.py        # SQLAlchemy ORM models (optional)
│
├── jobs/                # Background job processing
│   ├── __init__.py
│   ├── queue.py         # Job queue manager
│   ├── workers.py       # Job workers
│   └── tasks.py         # Job task definitions
│
├── utils/               # Shared utilities
│   ├── __init__.py
│   ├── hashing.py       # File/data hashing
│   ├── logging.py       # Logging configuration
│   └── exceptions.py    # Custom exceptions
│
├── scripts/             # Utility scripts
│   ├── init_db.py       # Database initialization
│   └── migrate.py       # Database migrations
│
├── tests/               # Test suite
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── requirements.txt     # Python dependencies
├── ARCHITECTURE.md      # Detailed architecture docs
└── DATABASE_SCHEMA.sql  # Database schema
```

## Environment Variables

Create `.env` file:

```env
# Database
DATABASE_PATH=./data/lucid.db

# Cache
CACHE_DIR=./data/cache
PARQUET_DIR=./data/parquet

# AI Service
AI_PROVIDER=openai  # or 'claude'
OPENAI_API_KEY=your_key_here
CLAUDE_API_KEY=your_key_here
AI_MODEL=gpt-4

# Server
API_HOST=127.0.0.1
API_PORT=8000
DEBUG=False

# Processing
MAX_WORKERS=4
JOB_TIMEOUT_SECONDS=300
```

## Development

```bash
# Run tests
pytest

# Format code
black .

# Lint
flake8 .

# Type check
mypy .
```

## Production

```bash
# Build
python -m build

# Run with production settings
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```
