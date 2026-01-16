"""Data validation for ingested data."""

import pandas as pd
from typing import Dict, List, Tuple, Optional
from utils.exceptions import ValidationError
from utils.logging import setup_logging

logger = setup_logging()


class ValidationResult:
    """Result of data validation."""
    
    def __init__(self, valid: bool, errors: List[str] = None, warnings: List[str] = None):
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def add_error(self, error: str):
        """Add validation error."""
        self.errors.append(error)
        self.valid = False
    
    def add_warning(self, warning: str):
        """Add validation warning."""
        self.warnings.append(warning)


def validate_sales_data(df: pd.DataFrame) -> ValidationResult:
    """
    Validate sales data schema and content.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        ValidationResult with validation status
    """
    result = ValidationResult(valid=True)
    
    # Core required columns for sales data (must exist in some form)
    required_columns = {
        'date': ['date', 'Date', 'DATE', 'transaction_date', 'sale_date'],
        'product_name': ['product_name', 'Product Name', 'product', 'item_name', 'party name', 'Party Name'],
        'total_amount': ['total_amount', 'Total Amount', 'Total', 'amount', 'total', 'sales_amount']
    }

    # Optional numeric columns we prefer but can derive if missing
    optional_columns = {
        'quantity': ['quantity', 'Quantity', 'qty', 'qty_sold'],
        'unit_price': ['unit_price', 'Unit Price', 'price', 'rate', 'selling_price']
    }
    
    # Check for required columns (flexible naming)
    found_columns = {}
    for required, alternatives in required_columns.items():
        found = None
        for alt in alternatives:
            if alt.lower() in [col.lower() for col in df.columns]:
                found = [col for col in df.columns if col.lower() == alt.lower()][0]
                break
        if not found:
            result.add_error(f"Missing required column: {required} (or alternatives: {alternatives})")
        else:
            found_columns[required] = found
    
    if not result.valid:
        return result
    # Try to locate optional columns
    for opt, alternatives in optional_columns.items():
        for alt in alternatives:
            if alt.lower() in [col.lower() for col in df.columns]:
                found_columns[opt] = [col for col in df.columns if col.lower() == alt.lower()][0]
                break
    
    # Rename columns to standard names
    column_mapping = {v: k for k, v in found_columns.items()}
    df_renamed = df.rename(columns=column_mapping)
    
    # Validate data types and ranges
    try:
        # Convert date column
        df_renamed['date'] = pd.to_datetime(df_renamed['date'], errors='coerce')
        invalid_dates = df_renamed['date'].isna().sum()
        if invalid_dates > 0:
            result.add_warning(f"{invalid_dates} rows have invalid dates")
        
        # Validate numeric columns
        numeric_cols = ['quantity', 'unit_price', 'total_amount']
        for col in numeric_cols:
            if col in df_renamed.columns:
                df_renamed[col] = pd.to_numeric(df_renamed[col], errors='coerce')
                invalid = df_renamed[col].isna().sum()
                if invalid > 0:
                    result.add_warning(f"{invalid} rows have invalid {col}")
                
                # Check for negative values
                negative = (df_renamed[col] < 0).sum()
                if negative > 0:
                    result.add_warning(f"{negative} rows have negative {col} values")
    except Exception as e:
        result.add_error(f"Data type validation failed: {str(e)}")
    
    # Check for duplicates
    if 'transaction_id' in df_renamed.columns:
        duplicates = df_renamed['transaction_id'].duplicated().sum()
        if duplicates > 0:
            result.add_warning(f"{duplicates} duplicate transaction IDs found")
    
    return result


def validate_inventory_data(df: pd.DataFrame) -> ValidationResult:
    """
    Validate inventory data schema and content.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        ValidationResult with validation status
    """
    result = ValidationResult(valid=True)
    
    # Required columns for inventory
    required_columns = {
        'product_name': ['product_name', 'Product Name', 'product', 'item_name'],
        'current_stock': ['current_stock', 'stock', 'quantity', 'qty', 'available_stock'],
        'unit_cost': ['unit_cost', 'cost', 'Cost', 'purchase_price', 'buying_price']
    }
    
    # Check for required columns
    found_columns = {}
    for required, alternatives in required_columns.items():
        found = None
        for alt in alternatives:
            if alt.lower() in [col.lower() for col in df.columns]:
                found = [col for col in df.columns if col.lower() == alt.lower()][0]
                break
        if not found:
            result.add_error(f"Missing required column: {required}")
        else:
            found_columns[required] = found
    
    if not result.valid:
        return result
    
    # Validate numeric columns
    numeric_cols = ['current_stock', 'unit_cost']
    for col in numeric_cols:
        if col in found_columns.values():
            col_name = found_columns[col]
            invalid = pd.to_numeric(df[col_name], errors='coerce').isna().sum()
            if invalid > 0:
                result.add_warning(f"{invalid} rows have invalid {col}")
    
    return result


def check_duplicates(df: pd.DataFrame, key_fields: List[str]) -> List[int]:
    """
    Check for duplicate rows based on key fields.
    
    Args:
        df: DataFrame to check
        key_fields: List of column names to use as key
        
    Returns:
        List of indices of duplicate rows
    """
    # Check which key fields exist
    existing_keys = [f for f in key_fields if f in df.columns]
    if not existing_keys:
        return []
    
    duplicates = df.duplicated(subset=existing_keys, keep='first')
    return df[duplicates].index.tolist()
