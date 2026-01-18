"""Ensure users table exists in database."""

import sqlite3
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

def ensure_users_table(db_path: str = "data/nafah.db"):
    """Ensure users table exists, create if missing."""
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("Users table not found. Creating...")
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    shop_name TEXT,
                    company_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            
            conn.commit()
            print("✅ Users table created successfully!")
        else:
            print("✅ Users table already exists.")
            
            # Check if shop_name column exists (for backward compatibility)
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'shop_name' not in columns:
                print("Adding shop_name and company_name columns...")
                cursor.execute("ALTER TABLE users ADD COLUMN shop_name TEXT")
                cursor.execute("ALTER TABLE users ADD COLUMN company_name TEXT")
                conn.commit()
                print("✅ Added shop_name and company_name columns.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = os.getenv("DATABASE_PATH", "data/nafah.db")
    ensure_users_table(db_path)
