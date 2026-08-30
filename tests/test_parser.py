"""
Unit tests for Excel Parser
"""
import pytest
from pathlib import Path
from app.parser import read_and_normalize_excel
from app.config import SAMPLE_DATA_DIR


def test_parse_valid_excel():
    file_path = SAMPLE_DATA_DIR / "sample_valid.xlsx"
    df, mapping = read_and_normalize_excel(file_path)
    assert not df.empty
    assert len(df) == 5
    assert "doc_type" in df.columns
    assert "booking_no" in df.columns
    assert "container_no" in df.columns


def test_parse_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        read_and_normalize_excel("nonexistent_file.xlsx")


def test_parse_invalid_extension(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("hello")
    with pytest.raises(ValueError, match="Unsupported file extension"):
        read_and_normalize_excel(txt_file)
