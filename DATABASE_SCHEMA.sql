-- Nafah Backend Database Schema
-- SQLite Database Schema for Local-First Analytics

-- Datasets table: Tracks all uploaded data sources
CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,  -- UUID v4
    name TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK(source_type IN ('csv', 'pdf', 'vyapar', 'excel')),
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,  -- SHA256 for change detection
    row_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'processing', 'completed', 'error')),
    error_message TEXT,
    user_id INTEGER NOT NULL,  -- Owner of the dataset
    is_shared BOOLEAN DEFAULT 0,  -- Whether dataset is shared with others
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_datasets_status ON datasets(status);
CREATE INDEX idx_datasets_source_type ON datasets(source_type);
CREATE INDEX idx_datasets_created_at ON datasets(created_at DESC);
CREATE INDEX idx_datasets_user_id ON datasets(user_id);
CREATE INDEX idx_datasets_is_shared ON datasets(is_shared);

-- Dataset sharing: Allows users to share datasets with team members
CREATE TABLE IF NOT EXISTS dataset_sharing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT NOT NULL,
    owner_id INTEGER NOT NULL,  -- User who owns the dataset
    shared_with_id INTEGER NOT NULL,  -- User with whom dataset is shared
    permission TEXT DEFAULT 'view' CHECK(permission IN ('view', 'edit')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (shared_with_id) REFERENCES users(id) ON DELETE CASCADE,
    
    UNIQUE(dataset_id, shared_with_id)
);

CREATE INDEX idx_dataset_sharing_dataset_id ON dataset_sharing(dataset_id);
CREATE INDEX idx_dataset_sharing_owner_id ON dataset_sharing(owner_id);
CREATE INDEX idx_dataset_sharing_shared_with_id ON dataset_sharing(shared_with_id);

-- Team invitations: Invite users to collaborate
CREATE TABLE IF NOT EXISTS team_invitations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inviter_id INTEGER NOT NULL,  -- User who sent the invitation
    invitee_email TEXT NOT NULL,  -- Email of user being invited
    dataset_id TEXT,  -- Optional: specific dataset to share
    token TEXT NOT NULL UNIQUE,  -- Unique invitation token
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'declined', 'expired')),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (inviter_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

CREATE INDEX idx_team_invitations_token ON team_invitations(token);
CREATE INDEX idx_team_invitations_invitee_email ON team_invitations(invitee_email);
CREATE INDEX idx_team_invitations_status ON team_invitations(status);

-- Raw sales data: Normalized sales transactions
CREATE TABLE IF NOT EXISTS raw_sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT NOT NULL,
    date DATE NOT NULL,
    product_name TEXT NOT NULL,
    product_id TEXT,
    quantity REAL NOT NULL CHECK(quantity >= 0),
    unit_price REAL NOT NULL CHECK(unit_price >= 0),
    total_amount REAL NOT NULL CHECK(total_amount >= 0),
    category TEXT,
    customer_id TEXT,
    transaction_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

CREATE INDEX idx_sales_dataset_id ON raw_sales(dataset_id);
CREATE INDEX idx_sales_date ON raw_sales(date);
CREATE INDEX idx_sales_product_name ON raw_sales(product_name);
CREATE INDEX idx_sales_product_id ON raw_sales(product_id);
CREATE INDEX idx_sales_category ON raw_sales(category);

-- Raw inventory data: Current stock levels
CREATE TABLE IF NOT EXISTS raw_inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT NOT NULL,
    product_name TEXT NOT NULL,
    product_id TEXT,
    current_stock REAL NOT NULL CHECK(current_stock >= 0),
    unit_cost REAL NOT NULL CHECK(unit_cost >= 0),
    category TEXT,
    last_updated DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    
    UNIQUE(dataset_id, product_id, product_name)
);

CREATE INDEX idx_inventory_dataset_id ON raw_inventory(dataset_id);
CREATE INDEX idx_inventory_product_name ON raw_inventory(product_name);
CREATE INDEX idx_inventory_product_id ON raw_inventory(product_id);
CREATE INDEX idx_inventory_category ON raw_inventory(category);

-- Analytics cache metadata: Tracks cached Parquet files
CREATE TABLE IF NOT EXISTS analytics_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT NOT NULL,
    cache_key TEXT NOT NULL,  -- e.g., 'best_sellers_2024', 'revenue_contribution'
    parquet_path TEXT NOT NULL,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_hash TEXT NOT NULL,  -- Hash of source data used for computation
    expires_at TIMESTAMP,
    
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    
    UNIQUE(dataset_id, cache_key)
);

CREATE INDEX idx_cache_dataset_id ON analytics_cache(dataset_id);
CREATE INDEX idx_cache_key ON analytics_cache(cache_key);
CREATE INDEX idx_cache_expires_at ON analytics_cache(expires_at);

-- Insights: Rule-based business insights
CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT NOT NULL,
    insight_id TEXT NOT NULL,  -- Unique identifier: 'dead_stock_001', 'seasonal_product_002'
    title TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('growth', 'risk', 'efficiency')),
    confidence TEXT NOT NULL CHECK(confidence IN ('high', 'medium', 'low')),
    supporting_metrics TEXT NOT NULL,  -- JSON object
    recommended_action TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

CREATE INDEX idx_insights_dataset_id ON insights(dataset_id);
CREATE INDEX idx_insights_category ON insights(category);
CREATE INDEX idx_insights_confidence ON insights(confidence);
CREATE INDEX idx_insights_active ON insights(is_active);
CREATE INDEX idx_insights_generated_at ON insights(generated_at DESC);

-- AI explanations: Cached natural language explanations
CREATE TABLE IF NOT EXISTS ai_explanations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_id INTEGER NOT NULL,
    explanation TEXT NOT NULL,
    guidance TEXT NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_used TEXT NOT NULL,  -- 'gpt-4', 'claude-3-opus', etc.
    prompt_hash TEXT,  -- Hash of prompt for cache invalidation
    
    FOREIGN KEY (insight_id) REFERENCES insights(id) ON DELETE CASCADE,
    
    UNIQUE(insight_id, prompt_hash)
);

CREATE INDEX idx_ai_explanations_insight_id ON ai_explanations(insight_id);
CREATE INDEX idx_ai_explanations_generated_at ON ai_explanations(generated_at DESC);

-- Processing jobs: Background job tracking
CREATE TABLE IF NOT EXISTS processing_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type TEXT NOT NULL CHECK(job_type IN ('ingestion', 'analytics', 'insights', 'ai_explanation')),
    dataset_id TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'running', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    metadata TEXT,  -- JSON for job-specific data
    
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE SET NULL
);

CREATE INDEX idx_jobs_status ON processing_jobs(status);
CREATE INDEX idx_jobs_dataset_id ON processing_jobs(dataset_id);
CREATE INDEX idx_jobs_type ON processing_jobs(job_type);
CREATE INDEX idx_jobs_created_at ON processing_jobs(created_at DESC);

-- Product master: Unified product catalog (optional, for cross-dataset analysis)
CREATE TABLE IF NOT EXISTS product_master (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    product_id TEXT,
    category TEXT,
    default_unit_cost REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(product_name, product_id)
);

CREATE INDEX idx_product_master_name ON product_master(product_name);
CREATE INDEX idx_product_master_category ON product_master(category);

-- Users table: User accounts for authentication
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    shop_name TEXT,
    company_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);

-- System configuration: App-level settings
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default config
INSERT OR IGNORE INTO system_config (key, value) VALUES
    ('ai_provider', 'openai'),
    ('ai_model', 'gpt-4'),
    ('cache_ttl_days', '30'),
    ('dead_stock_threshold_days', '90'),
    ('seasonality_min_score', '0.3');

-- Views for common queries

-- Active insights view
CREATE VIEW IF NOT EXISTS active_insights AS
SELECT 
    i.*,
    d.name as dataset_name,
    d.source_type
FROM insights i
JOIN datasets d ON i.dataset_id = d.id
WHERE i.is_active = 1
ORDER BY 
    CASE i.confidence 
        WHEN 'high' THEN 1 
        WHEN 'medium' THEN 2 
        WHEN 'low' THEN 3 
    END,
    i.generated_at DESC;

-- Dataset summary view
CREATE VIEW IF NOT EXISTS dataset_summary AS
SELECT 
    d.id,
    d.name,
    d.source_type,
    d.status,
    d.row_count,
    d.created_at,
    COUNT(DISTINCT rs.id) as sales_records,
    COUNT(DISTINCT ri.id) as inventory_records,
    COUNT(DISTINCT i.id) as insight_count,
    MAX(i.generated_at) as last_insight_at
FROM datasets d
LEFT JOIN raw_sales rs ON d.id = rs.dataset_id
LEFT JOIN raw_inventory ri ON d.id = ri.dataset_id
LEFT JOIN insights i ON d.id = i.dataset_id AND i.is_active = 1
GROUP BY d.id;
