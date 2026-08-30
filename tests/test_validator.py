"""
Unit tests for File Validator Engine
"""
import pytest
from app.validator import validate_ssr_file
from app.config import SAMPLE_DATA_DIR


def test_validate_valid_file():
    file_path = SAMPLE_DATA_DIR / "sample_valid.xlsx"
    result = validate_ssr_file(file_path)
    assert result.is_valid is True
    assert result.total_rows == 5
    assert result.valid_rows_count == 5
    assert len(result.errors) == 0
    assert len(result.jobs) == 3
    # Check deduplication: BKG1001 should have 2 unique containers (MSCU1234567, TGHU2345678)
    bkg1 = next(j for j in result.jobs if j.booking_no == "BKG1001")
    assert len(bkg1.containers) == 2
    assert bkg1.containers == ["MSCU1234567", "TGHU2345678"]


def test_validate_invalid_container():
    file_path = SAMPLE_DATA_DIR / "sample_invalid_container.xlsx"
    result = validate_ssr_file(file_path)
    assert result.is_valid is False
    assert len(result.errors) > 0
    assert any("Invalid container format" in err.error_message for err in result.errors)


def test_validate_missing_columns():
    file_path = SAMPLE_DATA_DIR / "sample_missing_columns.xlsx"
    result = validate_ssr_file(file_path)
    assert result.is_valid is False
    assert any("Missing mandatory column" in err.error_message for err in result.errors)


def test_validate_zero_rate():
    file_path = SAMPLE_DATA_DIR / "sample_zero_rate.xlsx"
    result = validate_ssr_file(file_path)
    assert result.is_valid is False
    assert any("rate" in err.column_name.lower() for err in result.errors)
