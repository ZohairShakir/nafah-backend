"""Dataset management endpoints."""

import uuid
import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Header, Depends
from typing import Optional
from datetime import datetime

from api.models.datasets import DatasetResponse, DatasetListResponse
from api.models.common import ErrorResponse
from storage.database import Database
from storage.cache import CacheManager
from utils.hashing import hash_file
from utils.exceptions import IngestionError
from utils.logging import setup_logging
from services.ingestion.parser import parse_file
from services.ingestion.validator import validate_sales_data, validate_inventory_data
from services.ingestion.normalizer import normalize_sales_data, normalize_inventory_data

# Import auth helper
import sys
from pathlib import Path as PathLib
sys.path.insert(0, str(PathLib(__file__).parent.parent.parent))
from api.routes.auth import sessions, get_current_user as auth_get_current_user

logger = setup_logging()

router = APIRouter(prefix="/api/v1/datasets", tags=["datasets"])

# Get database path from environment
DB_PATH = os.getenv("DATABASE_PATH", "data/nafah.db")
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

async def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current authenticated user from token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Extract token from "Bearer <token>" or just "<token>"
    token = authorization.replace("Bearer ", "").strip() if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="Authentication token required")
    
    user = await auth_get_current_user(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user

def _infer_schema_type_from_dataframe_columns(columns: list[str]) -> str:
    cols = {c.lower() for c in columns}
    # Simple heuristics:
    # - sales usually has date + quantity + price/amount
    # - inventory usually has current_stock + unit_cost
    if "date" in cols or "transaction_date" in cols or "sale_date" in cols:
        return "sales"
    if "current_stock" in cols or "stock" in cols:
        return "inventory"
    # fallback: if it looks like inventory (cost + stock)
    if ("unit_cost" in cols or "cost" in cols) and ("quantity" in cols or "stock" in cols):
        return "inventory"
    return "sales"

async def _store_sales_rows(db: Database, dataset_id: str, df) -> int:
    # Batch inserts in a transaction for performance
    queries: list[tuple[str, tuple]] = []
    insert_sql = (
        "INSERT INTO raw_sales "
        "(dataset_id, date, product_name, product_id, quantity, unit_price, total_amount, category, customer_id, transaction_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    for _, row in df.iterrows():
        queries.append(
            (
                insert_sql,
                (
                    dataset_id,
                    row["date"].date().isoformat() if hasattr(row["date"], "date") else str(row["date"]),
                    str(row.get("product_name", "")),
                    str(row.get("product_id", "")) if row.get("product_id") is not None else None,
                    float(row.get("quantity", 0) or 0),
                    float(row.get("unit_price", 0) or 0),
                    float(row.get("total_amount", 0) or 0),
                    str(row.get("category")) if row.get("category") is not None else None,
                    str(row.get("customer_id")) if row.get("customer_id") is not None else None,
                    str(row.get("transaction_id")) if row.get("transaction_id") is not None else None,
                ),
            )
        )
    await db.execute_transaction(queries)
    return len(df)

async def _store_inventory_rows(db: Database, dataset_id: str, df) -> int:
    queries: list[tuple[str, tuple]] = []
    insert_sql = (
        "INSERT OR REPLACE INTO raw_inventory "
        "(dataset_id, product_name, product_id, current_stock, unit_cost, category, last_updated) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
    for _, row in df.iterrows():
        last_updated = row.get("last_updated")
        if hasattr(last_updated, "date"):
            last_updated = last_updated.date().isoformat()
        elif last_updated is None:
            last_updated = datetime.now().date().isoformat()
        queries.append(
            (
                insert_sql,
                (
                    dataset_id,
                    str(row.get("product_name", "")),
                    str(row.get("product_id", "")) if row.get("product_id") is not None else None,
                    float(row.get("current_stock", 0) or 0),
                    float(row.get("unit_cost", 0) or 0),
                    str(row.get("category")) if row.get("category") is not None else None,
                    str(last_updated),
                ),
            )
        )
    await db.execute_transaction(queries)
    return len(df)


@router.post("", response_model=DatasetResponse, status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    name: Optional[str] = None,
    source_type: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    user: dict = Depends(get_current_user)
):
    """
    Upload a new dataset file.
    
    Args:
        file: Uploaded file (CSV, PDF, or Vyapar format)
        name: Optional dataset name
        source_type: Optional source type (auto-detected if not provided)
        
    Returns:
        Created dataset information
    """
    # Validate file
    # UploadFile.size is not guaranteed across servers; keep a soft check on content length instead.
    # The file will also be limited by the client and server config.
    if getattr(file, "size", None) and file.size > 100 * 1024 * 1024:  # 100MB limit
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 100MB."
        )
    
    # Generate dataset ID
    dataset_id = str(uuid.uuid4())
    
    # Save uploaded file
    file_extension = Path(file.filename).suffix.lower()
    saved_path = UPLOAD_DIR / f"{dataset_id}{file_extension}"
    
    try:
        with open(saved_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Compute file hash
        file_hash = hash_file(saved_path)
        
        # Check for duplicates
        db = Database(DB_PATH)
        existing = await db.execute_query(
            "SELECT id FROM datasets WHERE file_hash = ?",
            (file_hash,),
            fetch_one=True
        )
        
        if existing:
            # Delete uploaded file, return existing dataset
            saved_path.unlink()
            dataset = await db.get_dataset(existing['id'])
            if dataset:
                # Map 'id' to 'dataset_id' for Pydantic model
                dataset['dataset_id'] = dataset.pop('id', dataset.get('id'))
            return DatasetResponse(**dataset)
        
        # Auto-detect source type if not provided
        if not source_type:
            if file_extension == '.csv':
                source_type = 'csv'
            elif file_extension == '.pdf':
                source_type = 'pdf'
            elif file_extension in ['.xlsx', '.xls']:
                # For Excel files, try to detect if it's Vyapar based on filename or content
                # If filename contains 'vyapar', use 'vyapar', otherwise use 'excel' which will also be handled by Vyapar parser
                if 'vyapar' in file.filename.lower():
                    source_type = 'vyapar'
                else:
                    source_type = 'excel'  # Excel files will be parsed by Vyapar parser
            else:
                source_type = 'csv'  # Default
        
        # Use filename as name if not provided
        dataset_name = name or Path(file.filename).stem
        
        # Get user ID (required for authentication)
        user_id = user["id"] if user else None
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Create dataset record with user_id
        await db.execute_write(
            """
            INSERT INTO datasets 
            (id, name, source_type, file_path, file_hash, row_count, status, user_id, is_shared)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (dataset_id, dataset_name, source_type, str(saved_path), file_hash, 0, "pending", user_id, False)
        )
        
        # Mark as processing (we ingest synchronously for now)
        await db.update_dataset_status(dataset_id, "processing")

        # Ingest file into raw tables (deterministic, local)
        try:
            df_raw = parse_file(str(saved_path), source_type=source_type)
            schema_type = _infer_schema_type_from_dataframe_columns(list(df_raw.columns))

            if schema_type == "inventory":
                validation = validate_inventory_data(df_raw)
                if not validation.valid:
                    raise IngestionError("; ".join(validation.errors))
                df_norm = normalize_inventory_data(df_raw, source_type=source_type)
                row_count = await _store_inventory_rows(db, dataset_id, df_norm)
            else:
                validation = validate_sales_data(df_raw)
                if not validation.valid:
                    raise IngestionError("; ".join(validation.errors))
                df_norm = normalize_sales_data(df_raw, source_type=source_type)
                row_count = await _store_sales_rows(db, dataset_id, df_norm)

            await db.update_dataset_status(dataset_id, "completed", row_count=row_count)
        except Exception as ingest_err:
            logger.error(f"Ingestion failed for dataset {dataset_id}: {ingest_err}")
            await db.update_dataset_status(dataset_id, "error", error_message=str(ingest_err))
        
        # Get created dataset
        dataset = await db.get_dataset(dataset_id)
        
        # Map 'id' to 'dataset_id' for Pydantic model
        if dataset:
            dataset['dataset_id'] = dataset.pop('id', dataset.get('id'))
        
        return DatasetResponse(**dataset)
        
    except Exception as e:
        logger.error(f"Error uploading dataset: {e}")
        # Clean up on error
        if saved_path.exists():
            saved_path.unlink()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload dataset: {str(e)}"
        )


@router.get("", response_model=DatasetListResponse)
async def list_datasets(
    status: Optional[str] = Query(None, description="Filter by status"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    authorization: Optional[str] = Header(None),
    user: dict = Depends(get_current_user)
):
    """
    List all datasets for the authenticated user (their own + shared with them).
    
    Args:
        status: Optional status filter
        source_type: Optional source type filter
        limit: Maximum number of results
        offset: Pagination offset
        user: Authenticated user (from dependency)
        
    Returns:
        List of datasets
    """
    db = Database(DB_PATH)
    user_id = user["id"]
    
    # Query to get user's own datasets + datasets shared with them
    conditions = ["(d.user_id = ? OR ds.shared_with_id = ?)"]
    params = [user_id, user_id]
    
    if status:
        conditions.append("d.status = ?")
        params.append(status)
    if source_type:
        conditions.append("d.source_type = ?")
        params.append(source_type)
    
    where_clause = " AND ".join(conditions)
    
    # Get datasets with DISTINCT to avoid duplicates from JOIN
    query = f"""
        SELECT DISTINCT d.*
        FROM datasets d
        LEFT JOIN dataset_sharing ds ON d.id = ds.dataset_id
        WHERE {where_clause}
        ORDER BY d.created_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    
    datasets = await db.execute_query(query, tuple(params))
    
    # Get total count
    count_query = f"""
        SELECT COUNT(DISTINCT d.id) as total
        FROM datasets d
        LEFT JOIN dataset_sharing ds ON d.id = ds.dataset_id
        WHERE {where_clause}
    """
    total_result = await db.execute_query(count_query, tuple(params[:-2]), fetch_one=True)
    
    total = total_result['total'] if total_result else 0
    
    # Map 'id' to 'dataset_id' for each dataset
    mapped_datasets = []
    for d in datasets:
        d_copy = dict(d)
        d_copy['dataset_id'] = d_copy.pop('id', d_copy.get('id'))
        mapped_datasets.append(DatasetResponse(**d_copy))
    
    return DatasetListResponse(
        datasets=mapped_datasets,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    authorization: Optional[str] = Header(None),
    user: dict = Depends(get_current_user)
):
    """
    Get dataset by ID. Only returns if user owns it or has access via sharing.
    
    Args:
        dataset_id: Dataset identifier
        user: Authenticated user (from dependency)
        
    Returns:
        Dataset information
    """
    db = Database(DB_PATH)
    user_id = user["id"]
    
    # Check if user owns dataset or has access via sharing
    query = """
        SELECT d.*
        FROM datasets d
        LEFT JOIN dataset_sharing ds ON d.id = ds.dataset_id AND ds.shared_with_id = ?
        WHERE d.id = ? AND (d.user_id = ? OR ds.id IS NOT NULL)
    """
    result = await db.execute_query(query, (user_id, dataset_id, user_id), fetch_one=True)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset not found or access denied: {dataset_id}"
        )
    
    # Map 'id' to 'dataset_id' for Pydantic model
    result['dataset_id'] = result.pop('id', result.get('id'))
    
    return DatasetResponse(**result)


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    authorization: Optional[str] = Header(None),
    user: dict = Depends(get_current_user)
):
    """
    Delete a dataset and all associated data. Only owner can delete.
    
    Args:
        dataset_id: Dataset identifier
        user: Authenticated user (from dependency)
        
    Returns:
        Success message
    """
    db = Database(DB_PATH)
    user_id = user["id"]
    
    # Get dataset and verify ownership
    query = "SELECT * FROM datasets WHERE id = ? AND user_id = ?"
    dataset = await db.execute_query(query, (dataset_id, user_id), fetch_one=True)
    
    if not dataset:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset not found or you don't have permission to delete it: {dataset_id}"
        )
    
    try:
        # Delete file
        file_path = Path(dataset['file_path'])
        if file_path.exists():
            file_path.unlink()
        
        # Delete cache
        cache = CacheManager()
        cache.delete(dataset_id)
        
        # Delete from database (CASCADE will handle related records)
        await db.execute_write(
            "DELETE FROM datasets WHERE id = ?",
            (dataset_id,)
        )
        
        return {"success": True, "message": "Dataset deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting dataset: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete dataset: {str(e)}"
        )
