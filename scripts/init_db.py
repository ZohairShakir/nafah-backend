"""Initialize the Nafah database."""

import sqlite3
import sys
from pathlib import Path


def init_database(db_path: str = "data/nafah.db"):
    """
    Initialize the database with schema.
    
    Args:
        db_path: Path to database file
    """
    # Create data directory if it doesn't exist
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    
    # Get schema file path
    schema_file = Path(__file__).parent.parent / "DATABASE_SCHEMA.sql"
    
    if not schema_file.exists():
        print(f"Error: Schema file not found at {schema_file}")
        sys.exit(1)
    
    # Connect to database and execute schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        # Check if datasets table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='datasets'")
        table_exists = cursor.fetchone()
        
        # If database doesn't have required tables, recreate it
        if not table_exists:
            # Drop all existing tables and indexes if any
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table[0]}")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = cursor.fetchall()
            for index in indexes:
                # Skip sqlite_autoindex_* indexes
                if not index[0].startswith('sqlite_autoindex_'):
                    cursor.execute(f"DROP INDEX IF EXISTS {index[0]}")
            conn.commit()
        
        # Execute schema
        with open(schema_file, "r", encoding="utf-8") as f:
            schema_sql = f.read()
            # Replace CREATE INDEX with CREATE INDEX IF NOT EXISTS for compatibility
            schema_sql = schema_sql.replace("CREATE INDEX ", "CREATE INDEX IF NOT EXISTS ")
            schema_sql = schema_sql.replace("CREATE UNIQUE INDEX ", "CREATE UNIQUE INDEX IF NOT EXISTS ")
            conn.executescript(schema_sql)
        conn.commit()
        print(f"Database initialized successfully at {db_path}")
    except Exception as e:
        print(f"Error initializing database: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    db_path = os.getenv("DATABASE_PATH", "data/nafah.db")
    init_database(db_path)
