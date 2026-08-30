"""Checkpoint skip/resume and duplicate prevention."""
from app.checkpoint import CheckpointStore, COMPLETED, job_key
from app.models import InvoiceJob
from app.resilience import retry_call
from app.errors import LoginRequiredError, RetryExhaustedError, classify_exception, ErrorCategory


def _job(booking: str, container: str = "MSCU1234567") -> InvoiceJob:
    return InvoiceJob(
        booking_no=booking,
        doc_type="Export",
        invoice_to="Exporter",
        billing_party="PARTY",
        service="LIFT",
        rate=1000.0,
        containers=[container],
    )


def test_job_key_is_stable():
    a = _job("B1", "MSCU1234567")
    b = _job("B1", "MSCU1234567")
    assert job_key(a) == job_key(b)
    c = _job("B1", "TGHU2345678")
    assert job_key(a) != job_key(c)


def test_completed_jobs_are_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr("app.checkpoint.CHECKPOINT_DIR", tmp_path)
    jobs = [_job("B1"), _job("B2")]
    store = CheckpointStore.for_batch("f.xlsx", "f.xlsx", jobs)
    store.mark_completed(jobs[0], proof_path="proof.png")
    store2 = CheckpointStore.for_batch("f.xlsx", "f.xlsx", jobs)
    assert store2.is_completed(jobs[0]) is True
    assert store2.is_completed(jobs[1]) is False
    pending = store2.pending_jobs(jobs)
    assert [j.booking_no for j in pending] == ["B2"]
    assert store2.completed_count() == 1


def test_failed_job_is_not_treated_as_completed(tmp_path, monkeypatch):
    monkeypatch.setattr("app.checkpoint.CHECKPOINT_DIR", tmp_path)
    jobs = [_job("B1")]
    store = CheckpointStore.for_batch("f.xlsx", "f.xlsx", jobs)
    store.mark_failed(jobs[0], category="Timeout", message="slow", step="save")
    assert store.is_completed(jobs[0]) is False
    assert store.record(jobs[0])["retry_count"] == 1


def test_retry_call_stops_and_does_not_loop_forever(monkeypatch):
    monkeypatch.setattr("app.resilience.time.sleep", lambda _s: None)
    n = {"c": 0}

    def boom():
        n["c"] += 1
        raise RuntimeError("temp")

    try:
        retry_call(boom, attempts=3, description="unit")
        assert False, "should have raised"
    except RetryExhaustedError as e:
        assert n["c"] == 3
        assert e.retry_count == 3


def test_retry_call_does_not_retry_login():
    n = {"c": 0}

    def login():
        n["c"] += 1
        raise LoginRequiredError("login", step="nav", booking_no="B1")

    try:
        retry_call(login, attempts=5, description="nav")
        assert False
    except LoginRequiredError:
        assert n["c"] == 1


def test_classify_format_exception():
    err = RuntimeError('Portal threw FormatException on Save (empty tax percentage or rate).')
    assert classify_exception(err) == ErrorCategory.APPLICATION_ERROR
