"""
Excel File Reader & Column Normalizer
"""
from pathlib import Path
from typing import Tuple, Dict
import pandas as pd


def read_and_normalize_excel(file_path: str | Path) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Reads an Excel file and standardizes column names.
    
    Returns:
        Tuple of (normalized_df, column_mapping_dict)
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path.suffix.lower() not in [".xlsx", ".xls", ".xlsm"]:
        raise ValueError(f"Unsupported file extension '{path.suffix}'. Please provide an Excel (.xlsx/.xls) file.")

    # Read using pandas with openpyxl engine
    try:
        df = pd.read_excel(path, engine="openpyxl", dtype=str)
    except Exception as e:
        # Fallback without explicit engine for older xls formats
        df = pd.read_excel(path, dtype=str)

    if df.empty:
        raise ValueError("The uploaded Excel file is empty (no data found).")

    # Clean and map headers
    original_columns = list(df.columns)
    column_mapping = {}
    normalized_columns = []

    for col in original_columns:
        clean_col = str(col).strip().lower()
        clean_col = clean_col.replace(" ", "_").replace("-", "_").replace(".", "")
        normalized_columns.append(clean_col)
        column_mapping[clean_col] = str(col)

    df.columns = normalized_columns
    
    # Strip whitespace from string cells
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    
    return df, column_mapping
