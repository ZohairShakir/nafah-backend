"""Migration: Add user_id to datasets and create sharing tables."""

import sqlite3
import sys
from pathlib import Path


def migrate_database(db_path: str = "data/nafah.db"):
    """
    Migrate database to add user_id to datasets and create sharing tables.
    
    This migration:
    1. Adds user_id column to datasets (if not exists)
    2. Creates dataset_sharing table
    3. Creates team_invitations table
    """
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if user_id column exists
        cursor.execute("PRAGMA table_info(datasets)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Always check for shop_name in users table (independent of user_id check)
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [col[1] for col in cursor.fetchall()]
        
        if 'shop_name' not in user_columns:
            print("Adding shop_name column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN shop_name TEXT")
            cursor.execute("ALTER TABLE users ADD COLUMN company_name TEXT")
            print("[OK] Added shop_name and company_name columns to users")
        else:
            print("[OK] shop_name column already exists in users")
        
        if 'user_id' not in columns:
            print("Adding user_id column to datasets table...")
            # First, create a default user if users table is empty
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            if user_count == 0:
                print("No users found. Creating default user...")
                import hashlib
                default_email = "default@nafah.local"
                default_name = "Default User"
                default_shop_name = "My Store"
                default_password = hashlib.sha256("nafah123".encode()).hexdigest()
                # Check if shop_name column exists (should exist now from above)
                cursor.execute("PRAGMA table_info(users)")
                user_columns = [col[1] for col in cursor.fetchall()]
                if 'shop_name' in user_columns:
                    cursor.execute(
                        "INSERT INTO users (name, email, password_hash, shop_name) VALUES (?, ?, ?, ?)",
                        (default_name, default_email, default_password, default_shop_name)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                        (default_name, default_email, default_password)
                    )
                default_user_id = cursor.lastrowid
                print(f"Created default user with ID: {default_user_id}")
            else:
                # Use first user
                cursor.execute("SELECT id FROM users LIMIT 1")
                default_user_id = cursor.fetchone()[0]
                print(f"Using existing user with ID: {default_user_id}")
            
            # Add user_id column (allow NULL initially for existing datasets)
            cursor.execute("ALTER TABLE datasets ADD COLUMN user_id INTEGER")
            cursor.execute("ALTER TABLE datasets ADD COLUMN is_shared BOOLEAN DEFAULT 0")
            
            # Update existing datasets to use default user
            cursor.execute(
                "UPDATE datasets SET user_id = ? WHERE user_id IS NULL",
                (default_user_id,)
            )
            
            # Make user_id NOT NULL after populating
            # SQLite doesn't support ALTER COLUMN, so we need to recreate table
            # First, drop views that depend on datasets table
            try:
                cursor.execute("DROP VIEW IF EXISTS active_insights")
                cursor.execute("DROP VIEW IF EXISTS dataset_summary")
            except Exception:
                pass  # Views might not exist
            
            cursor.execute("""
                CREATE TABLE datasets_new (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source_type TEXT NOT NULL CHECK(source_type IN ('csv', 'pdf', 'vyapar', 'excel')),
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    row_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'processing', 'completed', 'error')),
                    error_message TEXT,
                    user_id INTEGER NOT NULL,
                    is_shared BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(file_hash)
                )
            """)
            cursor.execute("""
                INSERT INTO datasets_new 
                SELECT id, name, source_type, file_path, file_hash, row_count, 
                       created_at, updated_at, status, error_message, user_id, is_shared
                FROM datasets
            """)
            cursor.execute("DROP TABLE datasets")
            cursor.execute("ALTER TABLE datasets_new RENAME TO datasets")
            
            # Recreate views
            try:
                cursor.execute("""
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
                        i.generated_at DESC
                """)
                cursor.execute("""
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
                    GROUP BY d.id
                """)
            except Exception as e:
                print(f"Warning: Could not recreate views: {e}")
            
            # Recreate indexes
            cursor.execute("CREATE INDEX idx_datasets_status ON datasets(status)")
            cursor.execute("CREATE INDEX idx_datasets_source_type ON datasets(source_type)")
            cursor.execute("CREATE INDEX idx_datasets_created_at ON datasets(created_at DESC)")
            cursor.execute("CREATE INDEX idx_datasets_user_id ON datasets(user_id)")
            cursor.execute("CREATE INDEX idx_datasets_is_shared ON datasets(is_shared)")
            
            print("[OK] Added user_id and is_shared columns to datasets")
        else:
            print("[OK] user_id column already exists in datasets")
        
        # Create dataset_sharing table if it doesn't exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='dataset_sharing'
        """)
        if not cursor.fetchone():
            print("Creating dataset_sharing table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dataset_sharing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id TEXT NOT NULL,
                    owner_id INTEGER NOT NULL,
                    shared_with_id INTEGER NOT NULL,
                    permission TEXT DEFAULT 'view' CHECK(permission IN ('view', 'edit')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
                    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (shared_with_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(dataset_id, shared_with_id)
                )
            """)
            cursor.execute("CREATE INDEX idx_dataset_sharing_dataset_id ON dataset_sharing(dataset_id)")
            cursor.execute("CREATE INDEX idx_dataset_sharing_owner_id ON dataset_sharing(owner_id)")
            cursor.execute("CREATE INDEX idx_dataset_sharing_shared_with_id ON dataset_sharing(shared_with_id)")
            print("[OK] Created dataset_sharing table")
        else:
            print("[OK] dataset_sharing table already exists")
        
        # Create team_invitations table if it doesn't exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='team_invitations'
        """)
        if not cursor.fetchone():
            print("Creating team_invitations table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS team_invitations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inviter_id INTEGER NOT NULL,
                    invitee_email TEXT NOT NULL,
                    dataset_id TEXT,
                    token TEXT NOT NULL UNIQUE,
                    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'declined', 'expired')),
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (inviter_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX idx_team_invitations_token ON team_invitations(token)")
            cursor.execute("CREATE INDEX idx_team_invitations_invitee_email ON team_invitations(invitee_email)")
            cursor.execute("CREATE INDEX idx_team_invitations_status ON team_invitations(status)")
            print("[OK] Created team_invitations table")
        else:
            print("[OK] team_invitations table already exists")
        
        conn.commit()
        print(f"\n[OK] Migration completed successfully for {db_path}")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    db_path = os.getenv("DATABASE_PATH", "data/nafah.db")
    migrate_database(db_path)
