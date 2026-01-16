"""Parquet cache management."""

import pandas as pd
import pyarrow.parquet as pq
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from utils.exceptions import CacheError


class CacheManager:
    """Manages Parquet cache for analytics results."""
    
    def __init__(self, cache_dir: str = "data/parquet"):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_path(self, dataset_id: str, cache_key: str) -> Path:
        """
        Get path for cache file.
        
        Args:
            dataset_id: Dataset identifier
            cache_key: Cache key (e.g., 'best_sellers')
            
        Returns:
            Path to cache file
        """
        # Sanitize keys for filename
        safe_dataset_id = dataset_id.replace("-", "_")
        safe_cache_key = cache_key.replace("-", "_")
        return self.cache_dir / f"{safe_dataset_id}_{safe_cache_key}.parquet"
    
    def write(
        self,
        dataset_id: str,
        cache_key: str,
        data: pd.DataFrame
    ) -> Path:
        """
        Write data to cache.
        
        Args:
            dataset_id: Dataset identifier
            cache_key: Cache key
            data: DataFrame to cache
            
        Returns:
            Path to written cache file
        """
        try:
            cache_path = self.get_cache_path(dataset_id, cache_key)
            data.to_parquet(cache_path, index=False, engine='pyarrow')
            return cache_path
        except Exception as e:
            raise CacheError(f"Failed to write cache: {e}")
    
    def read(
        self,
        dataset_id: str,
        cache_key: str
    ) -> Optional[pd.DataFrame]:
        """
        Read data from cache.
        
        Args:
            dataset_id: Dataset identifier
            cache_key: Cache key
            
        Returns:
            DataFrame if cache exists, else None
        """
        try:
            cache_path = self.get_cache_path(dataset_id, cache_key)
            if cache_path.exists():
                return pd.read_parquet(cache_path, engine='pyarrow')
            return None
        except Exception as e:
            # If cache is corrupted, return None (will be regenerated)
            return None
    
    def exists(self, dataset_id: str, cache_key: str) -> bool:
        """Check if cache exists."""
        cache_path = self.get_cache_path(dataset_id, cache_key)
        return cache_path.exists()
    
    def delete(self, dataset_id: str, cache_key: Optional[str] = None) -> bool:
        """
        Delete cache file(s).
        
        Args:
            dataset_id: Dataset identifier
            cache_key: Specific cache key, or None to delete all for dataset
            
        Returns:
            True if deleted successfully
        """
        try:
            if cache_key:
                cache_path = self.get_cache_path(dataset_id, cache_key)
                if cache_path.exists():
                    cache_path.unlink()
            else:
                # Delete all caches for this dataset
                pattern = f"{dataset_id.replace('-', '_')}_*.parquet"
                for cache_file in self.cache_dir.glob(pattern):
                    cache_file.unlink()
            return True
        except Exception as e:
            raise CacheError(f"Failed to delete cache: {e}")
