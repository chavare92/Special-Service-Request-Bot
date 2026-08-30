"""
Pydantic Data Models & Schemas
"""
import re
from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator
from app.config import CONTAINER_REGEX, ALLOWED_DOC_TYPES

class SSRRow(BaseModel):
    """Represents a single parsed and validated row from the SSR Excel file."""
    row_number: int
    doc_type: str = Field(..., description="Document type, e.g., Export or Import")
    booking_no: str = Field(..., min_length=1, description="Booking or Bill of Lading Number")
    container_no: str = Field(..., description="11-character Container Number (e.g. MSCU1234567)")
    invoice_to: str = Field(..., min_length=1, description="Customer code / party to invoice")
    billing_party: str = Field(..., min_length=1, description="Billing party code")
    service: str = Field(..., min_length=1, description="Special service description/code")
    rate: float = Field(..., gt=0, description="Applicable rate, strictly greater than 0")

    @field_validator("doc_type")
    @classmethod
    def validate_doc_type(cls, v: str) -> str:
        clean = v.strip().title()
        if clean not in ALLOWED_DOC_TYPES:
            raise ValueError(f"Invalid doc_type '{v}'. Allowed values: {', '.join(ALLOWED_DOC_TYPES)}")
        return clean

    @field_validator("container_no")
    @classmethod
    def validate_container_no(cls, v: str) -> str:
        clean = re.sub(r"\s+", "", v.strip().upper())
        if not re.match(CONTAINER_REGEX, clean):
            raise ValueError(f"Invalid container format '{v}'. Expected 4 letters followed by 7 digits (e.g. MSCU1234567)")
        return clean

    @field_validator("booking_no", "invoice_to", "billing_party", "service")
    @classmethod
    def validate_non_empty_strings(cls, v: str) -> str:
        clean = str(v).strip()
        if not clean:
            raise ValueError("Field cannot be empty or whitespace only")
        return clean


class ValidationErrorDetail(BaseModel):
    """Detailed information for a single validation failure."""
    row_number: int
    column_name: str
    invalid_value: Any
    error_message: str


class InvoiceJob(BaseModel):
    """Grouped multi-container job for eLOGiPark entry."""
    booking_no: str
    doc_type: str
    invoice_to: str
    billing_party: str
    service: str
    rate: float
    containers: List[str]
    total_containers: int = 0

    def model_post_init(self, __context: Any) -> None:
        self.total_containers = len(self.containers)

    @property
    def total_amount(self) -> float:
        return round(self.rate * len(self.containers), 2)


class ValidationResult(BaseModel):
    """Encapsulates the complete result of parsing and validating an uploaded Excel file."""
    is_valid: bool
    file_path: str
    file_name: str
    total_rows: int = 0
    valid_rows_count: int = 0
    errors: List[ValidationErrorDetail] = []
    jobs: List[InvoiceJob] = []
    total_containers: int = 0
    total_amount: float = 0.0


class ExecutionSummary(BaseModel):
    """Summary of the attended bot execution run."""
    total_jobs: int = 0
    successful_jobs: int = 0
    failed_jobs: int = 0
    skipped_jobs: int = 0
    total_containers_processed: int = 0
    total_value_invoiced: float = 0.0
    proof_screenshots: List[str] = []
    errors: List[str] = []
    run_status: str = "completed"
    waiting_reason: str = ""
    resumed: bool = False
