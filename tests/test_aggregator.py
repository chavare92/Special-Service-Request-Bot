"""
Unit tests for Aggregator Module
"""
from app.models import SSRRow
from app.aggregator import aggregate_ssr_rows


def test_aggregator_multi_container_deduplication():
    rows = [
        SSRRow(
            row_number=2,
            doc_type="Export",
            booking_no="BKG001",
            container_no="MSCU1234567",
            invoice_to="ABC",
            billing_party="DPW",
            service="LIFT_ON",
            rate=5000.0
        ),
        SSRRow(
            row_number=3,
            doc_type="Export",
            booking_no="BKG001",
            container_no="TGHU2345678",
            invoice_to="ABC",
            billing_party="DPW",
            service="LIFT_ON",
            rate=5000.0
        ),
        SSRRow(
            row_number=4,
            doc_type="Export",
            booking_no="BKG001",
            container_no="MSCU1234567",  # Duplicate container
            invoice_to="ABC",
            billing_party="DPW",
            service="LIFT_ON",
            rate=5000.0
        ),
        SSRRow(
            row_number=5,
            doc_type="Export",
            booking_no="BKG002",
            container_no="CSNU3456789",
            invoice_to="XYZ",
            billing_party="DPW",
            service="LIFT_ON",
            rate=7500.0
        ),
    ]

    jobs = aggregate_ssr_rows(rows)
    assert len(jobs) == 2

    # Job 1
    job1 = jobs[0]
    assert job1.booking_no == "BKG001"
    assert len(job1.containers) == 2
    assert job1.containers == ["MSCU1234567", "TGHU2345678"]
    assert job1.total_amount == 10000.0

    # Job 2
    job2 = jobs[1]
    assert job2.booking_no == "BKG002"
    assert len(job2.containers) == 1
    assert job2.containers == ["CSNU3456789"]
    assert job2.total_amount == 7500.0
