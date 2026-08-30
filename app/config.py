"""
Application Configuration & Constants
"""
import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
COMPLETED_DIR = BASE_DIR / "completed"
LOGS_DIR = BASE_DIR / "logs"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"

# Ensure runtime directories exist
COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)

# eLOGiPark Portal URLs
ELOGIPARK_LOGIN_URL = "https://kribhcoinfra.in/elogipark/"
ELOGIPARK_HOME_URL = "https://kribhcoinfra.in/elogipark/Home.aspx"
# Live portal page (verified 200). Finance/SpecialServiceAdd.aspx is a 404.
ELOGIPARK_SSR_URL = "https://kribhcoinfra.in/elogipark/Commercial/SSInvoice.aspx"
ELOGIPARK_SSR_ADD_URL = ELOGIPARK_SSR_URL  # alias kept for older imports

# Validation Constants
CONTAINER_REGEX = r"^[A-Z]{4}\d{7}$"
ALLOWED_DOC_TYPES = ["Export", "Import"]
REQUIRED_COLUMNS = [
    "doc_type",
    "booking_no",
    "container_no",
    "invoice_to",
    "billing_party",
    "service",
    "rate"
]

# Browser Automation Timeouts (in ms)
DEFAULT_PAGE_TIMEOUT = 30000
DEFAULT_ACTION_TIMEOUT = 10000

# Retry / recovery (bounded — never infinite)
MAX_JOB_RETRIES = 2
MAX_ACTION_RETRIES = 3
RETRY_BACKOFF_SEC = (1.0, 2.5)
JOB_TIMEOUT_SEC = 180
BATCH_TIMEOUT_SEC = 3600

# Human-like pauses between portal actions (seconds, inclusive range)
HUMAN_DELAY_ACTION_SEC = (0.35, 0.90)
HUMAN_DELAY_NAV_SEC = (0.70, 1.40)
HUMAN_DELAY_BETWEEN_JOBS_SEC = (1.00, 2.20)

# Persistent checkpoints (resume without reprocessing completed bookings)
CHECKPOINT_DIR = LOGS_DIR / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

# UI Theme Config
APP_TITLE = "DP World — Special Service Request (SSR) Bot"
APP_VERSION = "2.2.0 (Attended Edition)"
