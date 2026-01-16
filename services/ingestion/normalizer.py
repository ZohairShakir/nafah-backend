"""Schema normalization for different data sources."""

import pandas as pd
from typing import Dict, Optional
from datetime import datetime
import re


def normalize_sales_data(
    df: pd.DataFrame,
    source_type: str = "csv"
) -> pd.DataFrame:
    """
    Normalize sales data to standard schema.
    
    Args:
        df: Raw DataFrame
        source_type: Source type for source-specific normalization
        
    Returns:
        Normalized DataFrame
    """
    df_normalized = df.copy()
    
    # Column name normalization (case-insensitive)
    # Vyapar-specific mappings are prioritized when source_type is 'vyapar'
    column_mapping = {}
    for col in df_normalized.columns:
        col_lower = col.lower().strip()
        # Date columns
        if 'date' in col_lower or 'transaction_date' in col_lower or 'invoice date' in col_lower:
            column_mapping[col] = 'date'
        # Product/Item name columns (Vyapar uses "Item Name" or "Party Name" for products)
        elif ('item' in col_lower and 'name' in col_lower) or ('product' in col_lower and 'name' in col_lower):
            column_mapping[col] = 'product_name'
        elif 'party name' in col_lower:
            # In Vyapar, "Party Name" in sales context often refers to products
            # In other systems, it can also refer to products
            if source_type == 'vyapar' and 'product_name' not in column_mapping.values():
                column_mapping[col] = 'product_name'
            elif source_type != 'vyapar':
                column_mapping[col] = 'product_name'
        # Product ID columns
        elif 'product_id' in col_lower or 'item_id' in col_lower or 'item code' in col_lower or 'hsn' in col_lower:
            column_mapping[col] = 'product_id'
        # Quantity columns (Vyapar uses "Qty" or "Quantity")
        elif 'quantity' in col_lower or 'qty' in col_lower:
            column_mapping[col] = 'quantity'
        # Price/Rate columns (Vyapar uses "Rate" or "Unit Price")
        elif ('unit' in col_lower and 'price' in col_lower) or 'rate' in col_lower or 'selling price' in col_lower:
            column_mapping[col] = 'unit_price'
        # Total amount columns (Vyapar uses "Amount" or "Total")
        elif 'total' in col_lower and 'amount' in col_lower:
            column_mapping[col] = 'total_amount'
        elif col_lower == 'amount' and 'total_amount' not in column_mapping.values():
            column_mapping[col] = 'total_amount'
        elif col_lower == 'total' and 'total_amount' not in column_mapping.values():
            column_mapping[col] = 'total_amount'
        # Category columns
        elif 'category' in col_lower or 'group' in col_lower:
            column_mapping[col] = 'category'
        # Customer/Party ID (Vyapar uses "Party Name" for customers in invoice context)
        elif 'customer' in col_lower and 'id' in col_lower:
            column_mapping[col] = 'customer_id'
        elif source_type == 'vyapar' and 'party name' in col_lower and 'customer_id' not in [v for v in column_mapping.values()]:
            # Store party name as customer_id if we already mapped product_name
            pass  # Skip - we use party name for product_name in Vyapar
        # Transaction/Invoice ID (Vyapar uses "Invoice No" or "Invoice Number")
        elif 'transaction' in col_lower and 'id' in col_lower:
            column_mapping[col] = 'transaction_id'
        elif ('invoice' in col_lower and ('no' in col_lower or 'number' in col_lower or 'id' in col_lower)):
            column_mapping[col] = 'transaction_id'
    
    # Apply mapping
    df_normalized = df_normalized.rename(columns=column_mapping)
    
    # Normalize date format
    if 'date' in df_normalized.columns:
        df_normalized['date'] = pd.to_datetime(df_normalized['date'], errors='coerce')
    
    # Normalize numeric columns
    numeric_cols = ['quantity', 'unit_price', 'total_amount']
    for col in numeric_cols:
        if col in df_normalized.columns:
            df_normalized[col] = pd.to_numeric(df_normalized[col], errors='coerce')

    # If quantity missing, assume 1 per row (e.g., Vyapar summary exports)
    if 'quantity' not in df_normalized.columns:
        df_normalized['quantity'] = 1.0

    # If unit_price missing but total_amount and quantity exist, derive it
    if 'unit_price' not in df_normalized.columns and 'total_amount' in df_normalized.columns:
        df_normalized['unit_price'] = df_normalized.apply(
            lambda row: row['total_amount'] / row['quantity'] if row.get('quantity', 0) not in (0, None) else row['total_amount'],
            axis=1
        )
    
    # Generate product_id if missing
    if 'product_id' not in df_normalized.columns and 'product_name' in df_normalized.columns:
        df_normalized['product_id'] = df_normalized['product_name'].apply(
            lambda x: generate_product_id(x, None)
        )
    
    # Ensure total_amount is calculated if missing
    if 'total_amount' not in df_normalized.columns:
        if 'quantity' in df_normalized.columns and 'unit_price' in df_normalized.columns:
            df_normalized['total_amount'] = (
                df_normalized['quantity'] * df_normalized['unit_price']
            )
    
    # Remove rows with critical missing data
    required_cols = ['date', 'product_name', 'quantity', 'total_amount']
    df_normalized = df_normalized.dropna(subset=required_cols)
    
    return df_normalized


def normalize_inventory_data(
    df: pd.DataFrame,
    source_type: str = "csv"
) -> pd.DataFrame:
    """
    Normalize inventory data to standard schema.
    
    Args:
        df: Raw DataFrame
        source_type: Source type for source-specific normalization
        
    Returns:
        Normalized DataFrame
    """
    df_normalized = df.copy()
    
    # Column name normalization
    column_mapping = {}
    for col in df_normalized.columns:
        col_lower = col.lower()
        if 'product' in col_lower and 'name' in col_lower:
            column_mapping[col] = 'product_name'
        elif 'product_id' in col_lower:
            column_mapping[col] = 'product_id'
        elif 'stock' in col_lower or 'quantity' in col_lower:
            column_mapping[col] = 'current_stock'
        elif 'cost' in col_lower or ('unit' in col_lower and 'cost' in col_lower):
            column_mapping[col] = 'unit_cost'
        elif 'category' in col_lower:
            column_mapping[col] = 'category'
        elif 'last' in col_lower and 'updated' in col_lower:
            column_mapping[col] = 'last_updated'
    
    df_normalized = df_normalized.rename(columns=column_mapping)
    
    # Normalize numeric columns
    numeric_cols = ['current_stock', 'unit_cost']
    for col in numeric_cols:
        if col in df_normalized.columns:
            df_normalized[col] = pd.to_numeric(df_normalized[col], errors='coerce')
    
    # Normalize date
    if 'last_updated' in df_normalized.columns:
        df_normalized['last_updated'] = pd.to_datetime(
            df_normalized['last_updated'],
            errors='coerce'
        )
    else:
        # Default to current date if missing
        df_normalized['last_updated'] = pd.Timestamp.now().date()
    
    # Generate product_id if missing
    if 'product_id' not in df_normalized.columns and 'product_name' in df_normalized.columns:
        df_normalized['product_id'] = df_normalized.apply(
            lambda row: generate_product_id(row.get('product_name'), row.get('category')),
            axis=1
        )
    
    return df_normalized


def generate_product_id(product_name: str, category: Optional[str] = None) -> str:
    """
    Generate a product ID from product name and category.
    
    Args:
        product_name: Product name
        category: Optional category
        
    Returns:
        Generated product ID
    """
    # Clean product name
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', str(product_name).upper())
    
    # Take first 8 characters
    name_part = clean_name[:8] if len(clean_name) >= 8 else clean_name.ljust(8, '0')
    
    # Add category prefix if available
    if category:
        clean_category = re.sub(r'[^a-zA-Z0-9]', '', str(category).upper())[:3]
        return f"{clean_category}_{name_part}"
    
    return f"PROD_{name_part}"
