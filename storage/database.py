"""SQLite database operations."""

import aiosqlite
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from utils.exceptions import DatabaseError


class Database:
    """Database manager for SQLite operations."""
    
    def __init__(self, db_path: str):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    async def execute_query(
        self,
        query: str,
        params: tuple = (),
        fetch_one: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query.
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch_one: If True, return single row
            
        Returns:
            List of dictionaries (or single dict if fetch_one=True)
        """
        try:
            async with aiosqlite.connect(str(self.db_path)) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute(query, params) as cursor:
                    if fetch_one:
                        row = await cursor.fetchone()
                        return dict(row) if row else None
                    else:
                        rows = await cursor.fetchall()
                        return [dict(row) for row in rows]
        except Exception as e:
            raise DatabaseError(f"Query execution failed: {e}")
    
    async def execute_write(
        self,
        query: str,
        params: tuple = (),
        return_id: bool = False
    ) -> Optional[int]:
        """
        Execute an INSERT/UPDATE/DELETE query.
        
        Args:
            query: SQL query string
            params: Query parameters
            return_id: If True, return last inserted row ID
            
        Returns:
            Last inserted row ID if return_id=True, else None
        """
        try:
            async with aiosqlite.connect(str(self.db_path)) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute(query, params)
                await conn.commit()
                if return_id:
                    return cursor.lastrowid
                return None
        except Exception as e:
            raise DatabaseError(f"Write operation failed: {e}")
    
    async def execute_transaction(self, queries: List[tuple]) -> bool:
        """
        Execute multiple queries in a transaction.
        
        Args:
            queries: List of (query, params) tuples
            
        Returns:
            True if successful
        """
        try:
            async with aiosqlite.connect(str(self.db_path)) as conn:
                conn.row_factory = aiosqlite.Row
                for query, params in queries:
                    await conn.execute(query, params)
                await conn.commit()
                return True
        except Exception as e:
            raise DatabaseError(f"Transaction failed: {e}")
    
    # Convenience methods for common operations
    
    async def create_dataset(
        self,
        dataset_id: str,
        name: str,
        source_type: str,
        file_path: str,
        file_hash: str,
        row_count: int = 0,
        status: str = "pending"
    ) -> None:
        """Create a new dataset record."""
        query = """
            INSERT INTO datasets 
            (id, name, source_type, file_path, file_hash, row_count, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        await self.execute_write(
            query,
            (dataset_id, name, source_type, file_path, file_hash, row_count, status)
        )
    
    async def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get dataset by ID."""
        query = "SELECT * FROM datasets WHERE id = ?"
        return await self.execute_query(query, (dataset_id,), fetch_one=True)
    
    async def list_datasets(
        self,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List datasets with optional filters."""
        conditions = []
        params = []
        
        if status:
            conditions.append("status = ?")
            params.append(status)
        if source_type:
            conditions.append("source_type = ?")
            params.append(source_type)
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT * FROM datasets
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        return await self.execute_query(query, tuple(params))
    
    async def update_dataset_status(
        self,
        dataset_id: str,
        status: str,
        row_count: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Update dataset status."""
        updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
        params = [status]
        
        if row_count is not None:
            updates.append("row_count = ?")
            params.append(row_count)
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)
        
        params.append(dataset_id)
        query = f"UPDATE datasets SET {', '.join(updates)} WHERE id = ?"
        await self.execute_write(query, tuple(params))
