"""
Script to clear all dataset data from the application.
This removes all datasets, sales data, inventory data, insights, and cache.
Use with caution - this cannot be undone!
"""

import asyncio
import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.database import Database
from storage.cache import CacheManager
from utils.logging import setup_logging

logger = setup_logging()

DB_PATH = os.getenv("DATABASE_PATH", "data/nafah.db")
UPLOAD_DIR = Path("data/uploads")
CACHE_DIR = Path("data/cache")


async def clear_all_data():
    """Clear all dataset data from the application."""
    db = Database(DB_PATH)
    
    print("⚠️  WARNING: This will delete ALL datasets and their data!")
    print("This includes:")
    print("  - All uploaded CSV files")
    print("  - All sales data")
    print("  - All inventory data")
    print("  - All insights")
    print("  - All cached analytics")
    print()
    
    response = input("Are you sure you want to proceed? Type 'yes' to confirm: ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    try:
        # Get all dataset IDs first
        datasets = await db.execute_query("SELECT id, name, file_path FROM datasets")
        dataset_ids = [d['id'] for d in datasets]
        
        print(f"\nFound {len(dataset_ids)} dataset(s) to delete...")
        
        # 1. Delete all uploaded files
        print("\n1. Deleting uploaded files...")
        deleted_files = 0
        for dataset in datasets:
            file_path = Path(dataset.get('file_path', ''))
            if file_path.exists():
                try:
                    file_path.unlink()
                    deleted_files += 1
                    print(f"   ✓ Deleted: {file_path.name}")
                except Exception as e:
                    print(f"   ✗ Failed to delete {file_path.name}: {e}")
        print(f"   Deleted {deleted_files} file(s)")
        
        # 2. Delete all cache entries
        print("\n2. Deleting cache entries...")
        cache = CacheManager()
        deleted_cache = 0
        for dataset_id in dataset_ids:
            try:
                cache.delete(dataset_id)
                deleted_cache += 1
            except Exception as e:
                print(f"   Warning: Could not delete cache for {dataset_id}: {e}")
        
        # Also clean up cache directory
        if CACHE_DIR.exists():
            import shutil
            try:
                shutil.rmtree(CACHE_DIR)
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                print(f"   ✓ Cleared cache directory")
            except Exception as e:
                print(f"   Warning: Could not clear cache directory: {e}")
        
        print(f"   Deleted cache for {deleted_cache} dataset(s)")
        
        # 3. Delete all database records
        print("\n3. Deleting database records...")
        
        # Delete raw sales data
        sales_count = await db.execute_query("SELECT COUNT(*) as count FROM raw_sales")
        sales_deleted = await db.execute_write(
            "DELETE FROM raw_sales"
        )
        print(f"   ✓ Deleted all sales data ({sales_count[0]['count'] if sales_count else 0} rows)")
        
        # Delete raw inventory data
        inventory_count = await db.execute_query("SELECT COUNT(*) as count FROM raw_inventory")
        await db.execute_write(
            "DELETE FROM raw_inventory"
        )
        print(f"   ✓ Deleted all inventory data ({inventory_count[0]['count'] if inventory_count else 0} rows)")
        
        # Delete insights
        insights_count = await db.execute_query("SELECT COUNT(*) as count FROM insights")
        await db.execute_write(
            "DELETE FROM insights"
        )
        print(f"   ✓ Deleted all insights ({insights_count[0]['count'] if insights_count else 0} rows)")
        
        # Delete analytics cache entries
        cache_count = await db.execute_query("SELECT COUNT(*) as count FROM analytics_cache")
        await db.execute_write(
            "DELETE FROM analytics_cache"
        )
        print(f"   ✓ Deleted analytics cache entries ({cache_count[0]['count'] if cache_count else 0} rows)")
        
        # Delete dataset sharing
        sharing_count = await db.execute_query("SELECT COUNT(*) as count FROM dataset_sharing")
        await db.execute_write(
            "DELETE FROM dataset_sharing"
        )
        print(f"   ✓ Deleted dataset sharing records ({sharing_count[0]['count'] if sharing_count else 0} rows)")
        
        # Finally delete datasets
        await db.execute_write(
            "DELETE FROM datasets"
        )
        print(f"   ✓ Deleted all datasets ({len(dataset_ids)} dataset(s))")
        
        print("\n✅ Successfully cleared all dataset data!")
        print("\nNote: User accounts are preserved. Only dataset-related data was deleted.")
        
    except Exception as e:
        logger.error(f"Error clearing data: {e}")
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(clear_all_data())
