"""
File Validation Engine with Granular Error Reporting
"""
from pathlib import Path
from typing import List, Tuple
import pandas as pd
from pydantic import ValidationError

from app.config import REQUIRED_COLUMNS
from app.models import SSRRow, ValidationErrorDetail, ValidationResult, InvoiceJob
from app.parser import read_and_normalize_excel
from app.aggregator import aggregate_ssr_rows


def validate_ssr_file(file_path: str | Path) -> ValidationResult:
    """
    Parses and validates an uploaded Excel file against all business and data rules.
    Returns a structured ValidationResult object.
    """
    path = Path(file_path)
    file_name = path.name

    # Step 1: Parse Excel
    try:
        df, column_mapping = read_and_normalize_excel(path)
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            file_path=str(path),
            file_name=file_name,
            total_rows=0,
            valid_rows_count=0,
            errors=[
                ValidationErrorDetail(
                    row_number=0,
                    column_name="File",
                    invalid_value=file_name,
                    error_message=f"Failed to read file: {str(e)}"
                )
            ]
        )

    # Step 2: Mandatory Columns Check
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        return ValidationResult(
            is_valid=False,
            file_path=str(path),
            file_name=file_name,
            total_rows=len(df),
            valid_rows_count=0,
            errors=[
                ValidationErrorDetail(
                    row_number=1,
                    column_name="Headers",
                    invalid_value=", ".join(df.columns),
                    error_message=f"Missing mandatory column(s): {', '.join(missing_columns)}"
                )
            ]
        )

    # Step 3: Row-by-Row Validation
    valid_rows: List[SSRRow] = []
    errors: List[ValidationErrorDetail] = []
    total_rows = len(df)

    for index, row in df.iterrows():
        excel_row_num = index + 2  # 1-indexed header is row 1, data starts at row 2

        # Extract values
        row_dict = {
            "row_number": excel_row_num,
            "doc_type": row.get("doc_type"),
            "booking_no": row.get("booking_no"),
            "container_no": row.get("container_no"),
            "invoice_to": row.get("invoice_to"),
            "billing_party": row.get("billing_party"),
            "service": row.get("service"),
            "rate": row.get("rate")
        }

        # Check for NaN / None
        for k, v in row_dict.items():
            if pd.isna(v) or v is None:
                row_dict[k] = ""

        # Rate numeric conversion check
        try:
            row_dict["rate"] = float(str(row_dict["rate"]).replace(",", ""))
        except (ValueError, TypeError):
            errors.append(
                ValidationErrorDetail(
                    row_number=excel_row_num,
                    column_name="rate",
                    invalid_value=row.get("rate"),
                    error_message="Rate must be a valid numeric number greater than 0"
                )
            )
            continue

        try:
            parsed_row = SSRRow(**row_dict)
            valid_rows.append(parsed_row)
        except ValidationError as val_err:
            for err in val_err.errors():
                loc = err.get("loc", ["unknown"])[0]
                msg = err.get("msg", "Invalid value")
                # Remove pydantic prefix if present
                clean_msg = msg.replace("Value error, ", "").replace("value is not a valid dict", "Invalid value")
                errors.append(
                    ValidationErrorDetail(
                        row_number=excel_row_num,
                        column_name=str(loc),
                        invalid_value=row.get(str(loc), ""),
                        error_message=clean_msg
                    )
                )

    is_valid = (len(errors) == 0 and len(valid_rows) > 0)
    jobs: List[InvoiceJob] = []
    total_containers = 0
    total_amount = 0.0

    if is_valid:
        jobs = aggregate_ssr_rows(valid_rows)
        total_containers = sum(j.total_containers for j in jobs)
        total_amount = round(sum(j.total_amount for j in jobs), 2)

    return ValidationResult(
        is_valid=is_valid,
        file_path=str(path),
        file_name=file_name,
        total_rows=total_rows,
        valid_rows_count=len(valid_rows),
        errors=errors,
        jobs=jobs,
        total_containers=total_containers,
        total_amount=total_amount
    )
