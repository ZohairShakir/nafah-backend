# Lucid Backend Design Summary

Complete backend architecture design for Lucid desktop-first analytics application.

## Design Overview

**Architecture Pattern**: Layered Architecture (API → Services → Storage)  
**Primary Language**: Python 3.11+  
**API Framework**: FastAPI  
**Database**: SQLite (local-first)  
**Analytics Cache**: Parquet files  
**AI Providers**: OpenAI / Claude (abstracted)  
**Background Processing**: Async job queue  

## Key Design Decisions

### 1. Local-First Architecture
- All data stored locally in SQLite
- No cloud dependency for core functionality
- AI calls optional (graceful degradation)

### 2. Deterministic Analytics
- All metrics computed via reproducible algorithms
- No ML models for analytics (only for explanations)
- Results cached in Parquet for performance

### 3. AI Isolation
- AI never receives raw data
- Only structured summaries (metrics + insights)
- Response validation prevents hallucinations

### 4. Rule-Based Insights
- No ML for insight generation
- Pure rule evaluation
- Confidence scoring based on data quality

### 5. Cached Computation
- Analytics cached until source data changes
- Hash-based cache invalidation
- Fast response times for repeated queries

## Component Summary

| Component | Purpose | Technology |
|-----------|---------|------------|
| **API Layer** | HTTP endpoints, validation | FastAPI, Pydantic |
| **Ingestion** | Parse CSV/PDF/Vyapar files | Pandas, PyPDF2 |
| **Analytics** | Compute business metrics | Pandas, DuckDB |
| **Insights** | Generate rule-based insights | Python rules engine |
| **AI Service** | Natural language explanations | OpenAI/Claude API |
| **Storage** | Data persistence | SQLite, Parquet |
| **Jobs** | Background processing | Async queue |

## Data Flow Summary

```
File Upload → Parse → Validate → Store → Invalidate Cache
                                    ↓
Request Analytics → Check Cache → Compute → Cache → Return
                                    ↓
Request Insights → Load Analytics → Evaluate Rules → Generate → Store → Return
                                    ↓
Request AI Explanation → Load Insights → Build Context → Call AI → Validate → Cache → Return
```

## Database Schema Summary

**8 Core Tables:**
1. `datasets` - Track uploaded files
2. `raw_sales` - Normalized sales transactions
3. `raw_inventory` - Current stock levels
4. `analytics_cache` - Cache metadata
5. `insights` - Generated insights
6. `ai_explanations` - Cached AI responses
7. `processing_jobs` - Background jobs
8. `product_master` - Product catalog (optional)

**2 Views:**
- `active_insights` - Filtered insights view
- `dataset_summary` - Aggregated dataset stats

## API Endpoints Summary

**Datasets (4 endpoints)**
- Upload, List, Get, Delete

**Analytics (7 endpoints)**
- Best sellers, Revenue contribution, Seasonality, Inventory velocity, Dead stock, Profitability, Trends

**Insights (2 endpoints)**
- List insights, Get specific insight

**AI (2 endpoints)**
- Generate explanation, Get cached explanation

**System (2 endpoints)**
- Health check, Force recompute

**Total: 17 endpoints**

## Analytics Capabilities

✅ Best-selling products (by quantity/revenue)  
✅ Revenue contribution percentages  
✅ Seasonal product detection (statistical)  
✅ Inventory velocity (turnover rates)  
✅ Dead stock detection (configurable threshold)  
✅ Profitability ranking (margins)  
✅ Month-over-month trends  

## Insight Categories

**Growth** (3+ rules)
- High-velocity low-stock
- Seasonal peak approaching
- Top sellers trending up

**Risk** (3+ rules)
- Dead stock identified
- Declining sales trends
- Overstock risk

**Efficiency** (3+ rules)
- Low-margin optimization
- High inventory costs
- Slow-moving categories

## Error Handling Strategy

**Layered Error Handling:**
1. **Validation**: Request-level (400)
2. **Business Logic**: Service-level (422)
3. **Not Found**: Resource-level (404)
4. **Processing**: Job-level (500)
5. **External Services**: AI/DB (503)

**Graceful Degradation:**
- Corrupted files: Skip bad rows, continue
- Missing data: Return partial results with warnings
- AI unavailable: Return insights without explanations
- Cache corruption: Auto-invalidate, recompute

## Performance Considerations

**Caching Strategy:**
- Analytics cached in Parquet (fast reads)
- Cache invalidated on data change (hash-based)
- AI explanations cached per insight

**Optimization:**
- Database indexes on all foreign keys
- Batch processing for large datasets
- Connection pooling for database
- Lazy loading of analytics

**Expected Performance:**
- Analytics computation: 1-5 seconds (first time)
- Cached analytics: <100ms
- Insight generation: 2-10 seconds
- AI explanation: 3-15 seconds (first time), <100ms (cached)

## Security Measures

1. **File Upload**: Size limits, format validation
2. **Input Validation**: All inputs validated via Pydantic
3. **SQL Injection**: Parameterized queries only
4. **Path Traversal**: Validated file paths
5. **API Keys**: Environment variables, never committed

## Implementation Phases

**Phase 1 (Week 1)**: Foundation
- FastAPI setup, database, basic CSV ingestion

**Phase 2 (Week 2-3)**: Core Analytics
- All analytics endpoints, caching

**Phase 3 (Week 4)**: Insights Engine
- Rule system, insight generation

**Phase 4 (Week 5)**: AI Integration
- AI service, explanation generation

**Phase 5 (Week 6)**: Background Jobs
- Job queue, async processing

**Total Estimated Time**: 6 weeks for solo developer

## File Structure

```
backend/
├── api/              # FastAPI application
├── services/        # Business logic
├── storage/         # Data persistence
├── jobs/            # Background processing
├── utils/           # Shared utilities
├── scripts/         # Utility scripts
├── tests/           # Test suite
└── docs/            # Documentation
```

## Dependencies Summary

**Core:**
- fastapi, uvicorn (API)
- pandas, duckdb (Analytics)
- aiosqlite (Database)
- pyarrow (Parquet)

**AI:**
- openai, anthropic (AI providers)

**Processing:**
- pypdf2, pdfplumber (PDF parsing)

**Dev:**
- pytest, black, flake8, mypy

## Key Files Created

1. **ARCHITECTURE.md** - Complete system architecture
2. **DATABASE_SCHEMA.sql** - Database schema with indexes
3. **MODULE_RESPONSIBILITIES.md** - Detailed module breakdown
4. **DATA_PIPELINES.md** - Flow diagrams and logic
5. **api/endpoints.md** - Complete API specification
6. **IMPLEMENTATION_GUIDE.md** - Step-by-step implementation
7. **requirements.txt** - Python dependencies
8. **README.md** - Quick start guide

## Next Steps

1. **Review Design**: Ensure alignment with requirements
2. **Set Up Environment**: Install dependencies, configure
3. **Start Phase 1**: Implement foundation
4. **Iterate**: Build incrementally, test frequently
5. **Integrate**: Connect with Tauri frontend

## Design Principles Applied

✅ **Separation of Concerns**: Clear layer boundaries  
✅ **Single Responsibility**: Each module has one purpose  
✅ **DRY**: Reusable utilities and services  
✅ **Fail-Safe**: Graceful error handling  
✅ **Performance**: Caching and optimization  
✅ **Maintainability**: Clear structure, documentation  
✅ **Testability**: Modular design, easy to test  
✅ **Scalability**: Can handle growth  

## Questions & Considerations

**Future Enhancements:**
- Multi-dataset analysis
- Data export features
- Real-time updates (WebSockets)
- Advanced visualizations
- Custom rule creation UI
- Data sync (optional cloud backup)

**Technical Debt:**
- Consider SQLAlchemy ORM for complex queries
- Add Redis for distributed job queue (if scaling)
- Implement database migrations system
- Add comprehensive logging/monitoring

---

**Design Status**: ✅ Complete  
**Ready for Implementation**: Yes  
**Estimated Implementation Time**: 6 weeks (solo developer)
