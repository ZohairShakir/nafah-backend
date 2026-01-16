"""File parsers for different formats."""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
from utils.exceptions import IngestionError
from utils.logging import setup_logging

logger = setup_logging()


def detect_format(file_path: str) -> str:
    """
    Detect file format from extension and content.
    
    Args:
        file_path: Path to file
        
    Returns:
        Format string: 'csv', 'pdf', 'vyapar', or 'excel'
    """
    extension = Path(file_path).suffix.lower()
    filename_lower = Path(file_path).name.lower()
    
    # Check if filename suggests Vyapar export
    if 'vyapar' in filename_lower or extension in ['.xlsx', '.xls']:
        # For Excel files, we'll check content to determine if it's Vyapar
        if extension in ['.xlsx', '.xls']:
            try:
                # Quick check: try to read Excel and look for Vyapar-like sheet names
                excel_file = pd.ExcelFile(file_path)
                sheets_lower = [s.lower() for s in excel_file.sheet_names]
                vyapar_indicators = ['sales', 'invoice', 'items', 'parties', 'purchase']
                if any(indicator in sheet for sheet in sheets_lower for indicator in vyapar_indicators):
                    return 'vyapar'
            except Exception:
                pass
        return 'vyapar' if 'vyapar' in filename_lower else 'excel'
    elif extension == '.csv':
        return 'csv'
    elif extension == '.pdf':
        return 'pdf'
    else:
        # Default to CSV for unknown formats
        return 'csv'


def parse_csv(
    file_path: str,
    schema_type: str = "sales"
) -> pd.DataFrame:
    """
    Parse CSV file.
    
    Args:
        file_path: Path to CSV file
        schema_type: Expected schema type ('sales', 'inventory', 'transactions')
        
    Returns:
        Parsed DataFrame
        
    Raises:
        IngestionError: If parsing fails
    """
    try:
        # Heuristic: detect header row for exports that include metadata lines
        header_row_index = 0
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                preview_lines = [next(f) for _ in range(8)]
            for idx, line in enumerate(preview_lines):
                lower = line.lower()
                if "date" in lower and ("total amount" in lower or "total" in lower):
                    header_row_index = idx
                    break
        except Exception:
            header_row_index = 0

        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    on_bad_lines='skip',
                    low_memory=False,
                    skiprows=header_row_index
                )
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            raise IngestionError("Failed to parse CSV with any encoding")
        
        if len(df) == 0:
            raise IngestionError("CSV file is empty or contains no valid rows")
        
        # Log parsing info
        logger.info(f"Parsed CSV: {len(df)} rows, {len(df.columns)} columns (header at row {header_row_index})")
        
        return df
        
    except pd.errors.EmptyDataError:
        raise IngestionError("CSV file is empty")
    except Exception as e:
        raise IngestionError(f"Failed to parse CSV: {str(e)}")


def parse_pdf(file_path: str) -> pd.DataFrame:
    """
    Parse PDF invoice/report (structured extraction using pdfplumber).
    
    Extracts tables and text from PDF to identify sales/invoice data.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        DataFrame with extracted data
        
    Raises:
        IngestionError: If parsing fails
    """
    try:
        import pdfplumber
        
        all_rows = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Try to extract tables first (most structured data)
                tables = page.extract_tables()
                
                if tables:
                    for table in tables:
                        # Convert table to rows
                        if len(table) > 1:  # Has header + data
                            # Use first row as header
                            headers = [str(cell or '').strip() if cell else '' for cell in table[0]]
                            # Process data rows
                            for row in table[1:]:
                                if row and any(cell for cell in row if cell):
                                    row_dict = {headers[i]: str(cell or '').strip() if cell else '' 
                                              for i, cell in enumerate(row) if i < len(headers)}
                                    if row_dict:
                                        all_rows.append(row_dict)
                
                # If no tables found, try extracting text and searching for patterns
                if not tables:
                    text = page.extract_text()
                    if text:
                        # Try to find invoice-like patterns in text
                        # This is a basic implementation - can be enhanced
                        lines = text.split('\n')
                        # Look for date patterns, amounts, product names
                        # For now, we'll return empty and rely on table extraction
                        pass
        
        if not all_rows:
            raise IngestionError("No extractable data found in PDF. Please ensure the PDF contains tables or structured data.")
        
        df = pd.DataFrame(all_rows)
        
        # Clean empty rows
        df = df.dropna(how='all')
        
        if len(df) == 0:
            raise IngestionError("PDF file contains no extractable data")
        
        logger.info(f"Parsed PDF: {len(df)} rows extracted")
        
        return df
        
    except ImportError:
        raise IngestionError("PDF parsing requires pdfplumber. Please install: pip install pdfplumber")
    except Exception as e:
        logger.error(f"PDF parsing error: {e}")
        raise IngestionError(f"Failed to parse PDF: {str(e)}")


def parse_vyapar(file_path: str) -> pd.DataFrame:
    """
    Parse Vyapar export file.
    
    Vyapar exports can be:
    - Excel files with multiple sheets (Items, Sales, Parties, Purchase, Payments)
    - CSV files with specific column structure
    
    Args:
        file_path: Path to Vyapar export file
        
    Returns:
        Parsed DataFrame (combined from multiple sheets if Excel)
        
    Raises:
        IngestionError: If parsing fails
    """
    try:
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension in ['.xlsx', '.xls']:
            # Excel file - parse all relevant sheets
            return _parse_vyapar_excel(file_path)
        else:
            # CSV file - parse with Vyapar-aware column detection
            return _parse_vyapar_csv(file_path)
    except Exception as e:
        raise IngestionError(f"Failed to parse Vyapar file: {str(e)}")


def _parse_vyapar_excel(file_path: str) -> pd.DataFrame:
    """
    Parse Vyapar Excel export with multiple sheets.
    
    Common Vyapar sheets:
    - Sales/Sales Invoice: Contains sales transactions
    - Items/Products: Product master data
    - Parties: Customer/Vendor data
    - Purchase: Purchase transactions
    - Payments: Payment records
    
    Returns combined sales DataFrame (prioritizing Sales sheet).
    """
    try:
        excel_file = pd.ExcelFile(file_path)
        sheets = excel_file.sheet_names
        
        logger.info(f"Vyapar Excel file contains sheets: {sheets}")
        
        # Prioritize sheets that contain sales data
        sales_sheets = ['Sales', 'Sales Invoice', 'Invoice', 'Sales Report', 'Sale']
        item_sheets = ['Items', 'Products', 'Product', 'Item Master']
        
        df_sales = None
        df_items = None
        
        # Find and parse sales sheet
        for sheet in sheets:
            if any(keyword.lower() in sheet.lower() for keyword in sales_sheets):
                df_sales = pd.read_excel(file_path, sheet_name=sheet)
                logger.info(f"Found sales data in sheet: {sheet} ({len(df_sales)} rows)")
                break
        
        # If no sales sheet found, try to find any sheet with date/product columns
        if df_sales is None or len(df_sales) == 0:
            for sheet in sheets:
                df_try = pd.read_excel(file_path, sheet_name=sheet, nrows=5)
                cols_lower = [c.lower() for c in df_try.columns]
                if any('date' in c or 'invoice' in c for c in cols_lower):
                    df_sales = pd.read_excel(file_path, sheet_name=sheet)
                    logger.info(f"Detected sales data in sheet: {sheet} ({len(df_sales)} rows)")
                    break
        
        # Parse items sheet for reference (can be used for validation)
        for sheet in sheets:
            if any(keyword.lower() in sheet.lower() for keyword in item_sheets):
                df_items = pd.read_excel(file_path, sheet_name=sheet)
                logger.info(f"Found items data in sheet: {sheet} ({len(df_items)} rows)")
                break
        
        if df_sales is None or len(df_sales) == 0:
            raise IngestionError("No sales data found in Vyapar Excel file. Expected sheets: Sales, Sales Invoice, or similar.")
        
        return df_sales
        
    except Exception as e:
        raise IngestionError(f"Failed to parse Vyapar Excel file: {str(e)}")


def _parse_vyapar_csv(file_path: str) -> pd.DataFrame:
    """
    Parse Vyapar CSV export with Vyapar-specific column detection.
    
    Vyapar CSV exports typically have columns like:
    - Date/Invoice Date
    - Party Name/Customer Name
    - Item Name/Product Name
    - Quantity/Qty
    - Rate/Unit Price
    - Amount/Total
    - HSN Code
    - GST/GST %
    """
    try:
        # Use the CSV parser but with Vyapar-aware header detection
        header_row_index = 0
        
        # Try to detect header row
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            preview_lines = [next(f) for _ in range(10)]
        
        for idx, line in enumerate(preview_lines):
            lower = line.lower()
            # Vyapar CSV markers
            if any(marker in lower for marker in ['date', 'invoice', 'party', 'item', 'amount']):
                header_row_index = idx
                break
        
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    on_bad_lines='skip',
                    low_memory=False,
                    skiprows=header_row_index
                )
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            raise IngestionError("Failed to parse Vyapar CSV with any encoding")
        
        if len(df) == 0:
            raise IngestionError("Vyapar CSV file is empty or contains no valid rows")
        
        logger.info(f"Parsed Vyapar CSV: {len(df)} rows, {len(df.columns)} columns")
        
        return df
        
    except Exception as e:
        raise IngestionError(f"Failed to parse Vyapar CSV: {str(e)}")


def parse_file(file_path: str, source_type: Optional[str] = None) -> pd.DataFrame:
    """
    Parse file based on detected or specified format.
    
    Args:
        file_path: Path to file
        source_type: Optional source type override
        
    Returns:
        Parsed DataFrame
    """
    if not source_type:
        source_type = detect_format(file_path)
    
    if source_type == 'csv':
        return parse_csv(file_path)
    elif source_type == 'pdf':
        # PDF parser now returns DataFrame directly
        return parse_pdf(file_path)
    elif source_type in ['vyapar', 'excel']:
        return parse_vyapar(file_path)
    else:
        raise IngestionError(f"Unsupported source type: {source_type}")
