"""
Multi-Container Aggregator & Deduplication Engine
"""
from collections import defaultdict
from typing import List, Tuple
from app.models import SSRRow, InvoiceJob


def aggregate_ssr_rows(rows: List[SSRRow]) -> List[InvoiceJob]:
    """
    Groups SSR rows by (booking_no, doc_type, invoice_to, billing_party, service, rate)
    and deduplicates container numbers within each group.
    
    Returns:
        List of InvoiceJob objects ready for automated entry.
    """
    # Key: (booking_no, doc_type, invoice_to, billing_party, service, rate)
    # Value: List of container numbers
    grouped_containers = defaultdict(list)

    for row in rows:
        key = (
            row.booking_no,
            row.doc_type,
            row.invoice_to,
            row.billing_party,
            row.service,
            row.rate
        )
        grouped_containers[key].append(row.container_no)

    jobs: List[InvoiceJob] = []
    for (bk, doc, inv, bp, svc, rate), containers in grouped_containers.items():
        # Deduplicate containers preserving order
        seen = set()
        unique_containers = []
        for c in containers:
            if c not in seen:
                seen.add(c)
                unique_containers.append(c)

        job = InvoiceJob(
            booking_no=bk,
            doc_type=doc,
            invoice_to=inv,
            billing_party=bp,
            service=svc,
            rate=rate,
            containers=unique_containers
        )
        jobs.append(job)

    return jobs
