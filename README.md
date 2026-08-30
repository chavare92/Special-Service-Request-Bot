# DP World — Special Service Request (SSR) Attended Automation Bot

An attended desktop automation bot developed in Python (PySide6) to streamline Special Service Request (SSR) invoicing on the **eLOGiPark Logistic Park Management System**.

---

## 🌟 Key Features

1. **Intuitive Attended Desktop UI**:
   - Drag-and-drop or browse Excel batch files (`.xlsx`, `.xls`, `.xlsm`).
   - Instant client-side validation against all data & business rules.
   - Granular diagnostics displaying exact row numbers, column names, and error causes.

2. **Secure Manual Login & Zero Credential Storage**:
   - Users log in directly on the official portal (`https://kribhcoinfra.in/elogipark/`) using their own credentials, terminal code, and MFA/OTP.
   - The bot **never** captures, requests, or stores user passwords or OTPs.

3. **Login State Verification**:
   - Only when the user clicks **"Start Bot"**, the application inspects the active browser to verify that the user is on `https://kribhcoinfra.in/elogipark/Home.aspx`.
   - If login verification fails, the application alerts the user and keeps execution safely halted until login is completed.

4. **Dynamic Container Grid Matcher**:
   - Groups multi-container rows by `(booking_no, invoice_to, billing_party, service, rate)`.
   - Deduplicates containers within booking groups.
   - Scans the portal's container table, ticks matching container checkboxes, inputs financial rates, checks *Invoice Checked*, and submits transactions.

5. **Audit Proof Screenshots & Real-Time Telemetry**:
   - Captures full-page screenshots for every processed invoice saved in `completed/`.
   - Real-time progress bar and live terminal log stream.

---

## 📋 Process Flow

```
[Upload / Browse Excel File]
       │
       ▼
[Validate File Rules]
   ├── ❌ Invalid ──► Display Errors in Diagnostics Table ──► Correct File
   └── ✅ Valid
       │
       ▼
[User Opens eLOGiPark & Logs In Manually]
       │
       ▼
[User Clicks "Start Bot"]
       │
       ▼
[Verify Login Status]
   ├── ❌ Login Failed ──► Display Error ──► Complete Login ──► Click "Start Bot" Again
   └── ✅ Login Verified
       │
       ▼
[Aggregate Multi-Container Bookings]
       │
       ▼
[Automate eLOGiPark Invoicing]
  • Open Commercial/SSInvoice.aspx (click Add if the form is disabled)
  • Select Doc Type & Booking No & Invoice To -> Click Go
  • Match & Tick Container Checkboxes in Grid, fill row Service / Qty / Rate
  • Enter Billing Party -> Tick 'Invoice Checked' -> Save
  • Capture Audit Screenshot Proof
       │
       ▼
[Display Batch Completion Summary]
```

---

## 📂 Project Directory Structure

```
SSR_Bot_Attended/
├── app/
│   ├── __init__.py
│   ├── config.py              # Configuration constants, URLs, timeouts, paths
│   ├── models.py              # Pydantic data schemas (SSRRow, InvoiceJob, ValidationResult)
│   ├── parser.py              # Excel reader & schema normalization (pandas/openpyxl)
│   ├── validator.py           # Multi-rule validation engine with granular row error reporting
│   ├── aggregator.py          # Multi-container grouping and deduplication logic
│   ├── browser_controller.py  # Playwright browser controller (launch, login check, form automation)
│   ├── worker.py              # Background QThread for non-blocking UI execution
│   └── logger.py              # Custom logger & UI log streaming bridge
├── ui/
│   ├── __init__.py
│   ├── main_window.py         # Main GUI window (layout, tabs, event bindings)
│   ├── drop_zone.py           # Custom Drag-and-Drop file upload component
│   ├── validation_table.py    # Visual table displaying parsed summary or validation errors
│   ├── log_viewer.py          # Real-time streaming log display
│   ├── status_panel.py        # Progress bar, status indicators, and action buttons
│   └── styles.py              # Dark/Light theme styling definitions
├── completed/                 # Destination directory for audit screenshots
├── logs/                      # Application execution logs (ssr_bot.log)
├── sample_data/               # Sample valid and invalid Excel templates for testing
├── tests/
│   ├── test_validator.py      # Unit tests for validation engine
│   ├── test_aggregator.py     # Unit tests for multi-container grouping
│   └── test_parser.py         # Unit tests for Excel parsing
├── requirements.txt           # Python dependencies
├── main.py                    # Application entry point
└── README.md                  # User manual & documentation
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Microsoft Edge or Google Chrome installed on Windows

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Application
```bash
python main.py
```

### 4. Run Unit Tests
```bash
pytest -v
```

---

## 📊 Excel File Format Specification

The uploaded Excel sheet must contain the following mandatory columns:

| Column Name | Expected Type | Description / Constraints |
|:---|:---|:---|
| `doc_type` | String | Must be `Export` or `Import` |
| `booking_no` | String | Booking or Bill of Lading reference |
| `container_no` | String | 11-char ISO container ID (e.g. `MSCU1234567`) |
| `invoice_to` | String | Customer / Party code to invoice |
| `billing_party`| String | Billing party code (e.g. `DPW_PANIPAT`) |
| `service` | String | Service name / code (e.g. `SPECIAL_LIFT_ON`) |
| `rate` | Numeric | Numeric value $> 0$ |
