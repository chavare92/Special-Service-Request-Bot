"""
Playwright Browser Controller with CDP (Chrome DevTools Protocol).

Navigates the live eLOGiPark Special Service Invoice screen
(Commercial/SSInvoice.aspx) using ContentPlaceHolder-prefixed selectors.
"""
import os
import socket
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Callable

from playwright.sync_api import sync_playwright

from app.config import (
    ELOGIPARK_LOGIN_URL,
    ELOGIPARK_HOME_URL,
    ELOGIPARK_SSR_URL,
    DEFAULT_PAGE_TIMEOUT,
    COMPLETED_DIR,
)
from app.errors import LoginRequiredError, SessionNotFoundError, WebsiteUnavailableError
from app.models import InvoiceJob
from app.resilience import human_pause

CDP_PORT = 9222
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"
BROWSER_PROFILE_DIR = Path.home() / ".ssr_bot_browser_profile"

# Live ASP.NET IDs from Commercial/SSInvoice.aspx (ctl00_ContentPlaceHolder1_*).
SEL_DOC_TYPE = [
    "select#ctl00_ContentPlaceHolder1_lstDocType",
    "select[id$='lstDocType']",
    "select[id*='lstDocType']",
    "select[id*='DocType']",
]
SEL_BOOKING = [
    "input#ctl00_ContentPlaceHolder1_textBookingNo",
    "input[id$='textBookingNo']",
    "input[id*='textBookingNo']",
    "input[id*='BookingNo']",
    "input[id*='Booking']",
]
SEL_INVOICE_TO = [
    "select#ctl00_ContentPlaceHolder1_lstInvoiceTo",
    "select[id$='lstInvoiceTo']",
    "select[id*='lstInvoiceTo']",
    "select[id*='InvoiceTo']",
]
SEL_BILL_PARTY = [
    "select#ctl00_ContentPlaceHolder1_LstBiitoPartyNamne",
    "select[id$='LstBiitoPartyNamne']",
    "select[id*='BiitoParty']",
    "select[id*='LstBiito']",
    "select[id*='PartyNam']",
    "select[id*='Billparty']",
    "select[id*='BillParty']",
    "select[id*='BillingParty']",
    "select[title*='Bill Party']",
    "select[title*='BillParty']",
]
SEL_SERVICE_TYPE = [
    "select#ctl00_ContentPlaceHolder1_lstServiceType",
    "select[id$='lstServiceType']",
    "select[id*='lstServiceType']",
]
SEL_GO = [
    "input#ctl00_ContentPlaceHolder1_btnGo",
    "input[id$='btnGo']",
    "input[id*='btnGo']",
    "input[id*='BtnGo']",
    "input[value='Go']",
    "input[value='GO']",
    "button:has-text('Go')",
]
# Live form: GO beside Booking No, then a second GO beside Invoice To.
SEL_BOOKING_GO = [
    "input#ctl00_ContentPlaceHolder1_btnAddBooking",
    "input[id$='btnAddBooking']",
    "input[name*='btnAddBooking']",
]
SEL_INVOICE_TO_GO = [
    "input#ctl00_ContentPlaceHolder1_BtnInvoiceTo",
    "input[id$='BtnInvoiceTo']",
    "input[name*='BtnInvoiceTo']",
]
SEL_SAVE = [
    "input#ctl00_ContentPlaceHolder1_btnSave",
    "input[id$='btnSave']",
    "input[id*='btnSave']",
    "input[id*='BtnSave']",
    "input[value='Save']",
    "input[value='SAVE']",
    "button:has-text('Save')",
]
SEL_ADD = [
    "input#ctl00_ContentPlaceHolder1_btnAdd",
    "input#btnAdd",
    "input[id$='btnAdd']",
    "input[id*='btnAdd']",
    "input[id*='BtnAdd']",
    "input[type='submit'][value='ADD']",
    "input[type='submit'][value='Add']",
    "input[value='ADD']",
    "input[value='Add']",
    "button:has-text('ADD')",
    "button:has-text('Add')",
]
SEL_INVOICE_CHECKED = [
    "input#ctl00_ContentPlaceHolder1_chkInvoiceChecked",
    "input[id$='chkInvoiceChecked']",
    "input[id*='InvoiceChecked']",
    "input[id*='chkInvoice']",
]
SEL_LOGIN_FORM = "input#textUserName, input#textPassword, input#btnLogIn"
SEL_OTP = "input#TxtOTP, input#txtOtp, input#txtOTP, input[id*='OTP']"


def is_cdp_port_open(timeout: float = 1.0) -> bool:
    """TCP check for the CDP port — safe to call from the Qt GUI thread."""
    try:
        with socket.create_connection(("127.0.0.1", CDP_PORT), timeout=timeout):
            return True
    except OSError:
        return False


def is_aspnet_error_page(title: str, body: str = "") -> bool:
    """True when the portal returned the ASP.NET 404 / server-error shell."""
    blob = f"{title} {body}".lower()
    return any(
        token in blob
        for token in (
            "the resource cannot be found",
            "server error in",
            "http 404",
            "not in a correct format",
            "unhandled exception",
            "formatexception",
            "invalidcastexception",
        )
    )


def is_portal_success_message(text: str) -> bool:
    """eLOGiPark puts both success and errors in lblErrorMessage."""
    blob = (text or "").strip().lower()
    if not blob:
        return False
    return any(
        token in blob
        for token in (
            "saved successfully",
            "save successfully",
            "successfully saved",
            "record saved",
            "invoice saved",
        )
    )


def form_button_matches(value: str, text: str, names: List[str]) -> bool:
    """Match an ASP.NET submit button by value or inner text (case-insensitive)."""
    label = (value or text or "").strip().upper()
    wanted = {n.strip().upper() for n in names if n}
    return bool(label) and label in wanted


def find_browser_executable() -> str:
    """Finds installed Microsoft Edge or Google Chrome executable on Windows."""
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return "msedge.exe"


class BrowserController:
    """
    Controls MS Edge / Chrome via CDP.

    Playwright Sync is only used from background QThreads (login check + invoicing).
    The GUI thread uses a TCP port check and subprocess.Popen only.
    """

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    def launch_interactive_browser(self, start_url: str = ELOGIPARK_LOGIN_URL) -> bool:
        """
        Launch Edge/Chrome with remote debugging.

        If CDP is already listening, leave the existing session alone so the
        operator does not lose an in-progress login.
        """
        if is_cdp_port_open():
            return True

        exe = find_browser_executable()
        cmd = [
            exe,
            f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={BROWSER_PROFILE_DIR}",
            "--start-maximized",
            "--no-first-run",
            "--no-default-browser-check",
            start_url,
        ]

        try:
            self._proc = subprocess.Popen(cmd)
        except Exception as e:
            raise RuntimeError(f"Failed to launch browser '{exe}': {str(e)}")

        deadline = time.time() + 10
        while time.time() < deadline:
            if is_cdp_port_open():
                time.sleep(0.4)
                return True
            time.sleep(0.25)

        return True

    def is_browser_open(self) -> bool:
        """Qt-safe: does not create a Playwright session."""
        return is_cdp_port_open()

    def verify_login_status(self) -> Tuple[bool, str]:
        """Inspect the live tab. Call from a worker thread, not the Qt GUI thread."""
        if not is_cdp_port_open():
            return False, "Browser is not open. Please click 'Open eLOGiPark Portal' to open the portal."

        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(CDP_URL, timeout=5000)
                context = browser.contexts[0] if browser.contexts else None
                if not context or not context.pages:
                    browser.close()
                    return False, "Browser is open but has no tabs. Please open the eLOGiPark portal and log in."

                pages = [pg for pg in reversed(context.pages) if not pg.is_closed()]
                last_url = pages[0].url if pages else "Unknown"

                for page in pages:
                    url = page.url.strip()
                    url_lower = url.lower()
                    title = ""
                    try:
                        title = page.title()
                    except Exception:
                        pass

                    if is_aspnet_error_page(title):
                        continue

                    if self._login_form_visible(page):
                        browser.close()
                        return False, (
                            f"Browser is currently on the login page ({url}). "
                            "Please enter your credentials, terminal code, solve captcha, log in, "
                            "and click 'Start Bot' again."
                        )

                    if self._otp_form_visible(page):
                        browser.close()
                        return False, (
                            f"You are currently on the OTP/MFA screen ({url}). "
                            "Please enter your OTP in the browser, complete login, then click 'Start Bot'."
                        )

                    # Default2.aspx is the unauthenticated Terminal/CTO chooser, not Home.
                    if "default2.aspx" in url_lower:
                        continue

                    user_label = self._logged_in_user(page)
                    if user_label:
                        page.bring_to_front()
                        browser.close()
                        return True, f"Verified logged in as {user_label} (Page: {url})"

                    # Home.aspx is the authenticated dashboard. Default2.aspx is not.
                    if "home.aspx" in url_lower:
                        page.bring_to_front()
                        browser.close()
                        return True, f"Verified logged in (Page: {url})"

                    # Unauthenticated SSInvoice still returns 200 with a disabled form.
                    if "ssinvoice" in url_lower:
                        booking = self._find_element(page, SEL_BOOKING)
                        if booking and booking.is_enabled():
                            page.bring_to_front()
                            browser.close()
                            return True, f"Verified logged in (Special Service form is active: {url})"
                        continue

                browser.close()
                return False, (
                    f"Not logged in. Current page: {last_url}. Expected: {ELOGIPARK_HOME_URL} "
                    "after a completed login."
                )
        except Exception as e:
            return False, f"Error inspecting browser state: {str(e)}"

    def process_job(
        self,
        job: InvoiceJob,
        log_callback: Optional[Callable[[str], None]] = None,
        step_callback: Optional[Callable[[str], None]] = None,
        abort_check: Optional[Callable[[], bool]] = None,
    ) -> str:
        """Run one Special Service invoice. Must be called from a worker thread."""

        def log(msg: str):
            if log_callback:
                log_callback(msg)

        def step(name: str):
            if abort_check and abort_check():
                raise RuntimeError("Cancelled by user.")
            if step_callback:
                step_callback(name)
            log(f"Checkpoint step: {name}")

        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(CDP_URL, timeout=10000)
            except Exception as e:
                raise SessionNotFoundError(
                    "Browser session was not found. Open eLOGiPark, log in, then click Start Bot to resume.",
                    step="connect",
                    booking_no=job.booking_no,
                ) from e
            context = browser.contexts[0] if browser.contexts else None
            if not context:
                raise SessionNotFoundError(
                    "No browser tab is open. Please open the eLOGiPark portal and log in.",
                    step="connect",
                    booking_no=job.booking_no,
                )
            page = self._find_or_create_portal_page(context)
            page.set_default_timeout(DEFAULT_PAGE_TIMEOUT)
            page.bring_to_front()

            self._assert_portal_ok(page, "login_check", job.booking_no)

            step("navigate")
            log(f"Navigating to Special Service Invoice for Booking #{job.booking_no}...")
            self._navigate_to_special_service_page(page, log)
            self._assert_portal_ok(page, "navigate", job.booking_no)
            human_pause("nav")

            step("header")
            log(
                f"Filling header: DocType={job.doc_type}, Booking={job.booking_no}, "
                f"InvoiceTo={job.invoice_to}"
            )

            # Doc Type auto-posts back; Booking often stays locked until Doc Type is set.
            doc_type_sel = self._require_selector(page, SEL_DOC_TYPE, "Doc Type")
            self._select_dropdown(page, doc_type_sel, job.doc_type, "Doc Type")
            self._wait_settled(page, extra_s=1.0)
            if not self._wait_booking_enabled(page, timeout_ms=15000):
                log("Booking No still disabled after Doc Type — continuing to try fill.")

            step("booking")
            booking_sel = self._require_selector(page, SEL_BOOKING, "Booking No")
            self._fill_enabled(page, booking_sel, job.booking_no, "Booking No")

            log("Clicking GO next to Booking No to load the booking...")
            if not self._click_control(page, SEL_BOOKING_GO, log_func=log):
                raise RuntimeError(
                    "Could not find the GO button beside Booking No "
                    "(expected #ctl00_ContentPlaceHolder1_btnAddBooking)."
                )
            self._wait_after_booking_go(page)
            self._assert_portal_ok(page, "booking_go", job.booking_no)
            self._raise_if_portal_error(page, "after Booking GO")
            human_pause("nav")

            step("invoice_to")
            inv_sel = self._require_selector(page, SEL_INVOICE_TO, "Invoice To")
            self._select_dropdown(page, inv_sel, job.invoice_to, "Invoice To")
            self._wait_settled(page, extra_s=0.4)

            log("Clicking GO next to Invoice To to load party and containers...")
            if not self._click_control(page, SEL_INVOICE_TO_GO, log_func=log):
                log("Invoice To GO not found — trying generic GO.")
                self._click_form_button(page, ["GO", "Go", "Search"], log)
            self._wait_settled(page, extra_s=1.2)
            self._assert_portal_ok(page, "invoice_to_go", job.booking_no)
            self._raise_if_portal_error(page, "after Invoice To GO")
            self._wait_bill_party_ready(page)
            human_pause("action")

            step("billing_party")
            log(
                f"Populating financials: BillingParty={job.billing_party}, "
                f"Service={job.service}, Rate={job.rate}"
            )
            bp_sel = self._require_selector(page, SEL_BILL_PARTY, "Billing Party")
            self._select_dropdown(page, bp_sel, job.billing_party, "Billing Party")
            self._wait_settled(page, extra_s=0.8)

            step("containers")
            self._wait_for_container_values(page, timeout_ms=15000)

            log(
                f"Scanning container grid for {len(job.containers)} target container(s): "
                f"{', '.join(job.containers)}"
            )
            matched_containers = self._match_and_fill_container_rows(page, job, log)

            missing = set(c.upper() for c in job.containers) - set(c.upper() for c in matched_containers)
            if missing:
                found_all = self._read_container_values(page)
                err_screenshot = self._save_screenshot(page, f"missing_containers_{job.booking_no}")
                title = page.title()
                page_url = page.url
                browser.close()
                if is_aspnet_error_page(title):
                    raise RuntimeError(
                        f"Landed on an error page instead of the container grid "
                        f"(URL: {page_url}, title: {title}). Screenshot: {err_screenshot}"
                    )
                raise RuntimeError(
                    f"Container match mismatch on booking #{job.booking_no}. "
                    f"Missing: {sorted(missing)}. Portal grid had: {found_all or '[]'}. "
                    f"Error screenshot saved: {err_screenshot}"
                )

            svc_type_sel = self._find_selector(page, SEL_SERVICE_TYPE)
            if svc_type_sel:
                try:
                    self._select_dropdown(page, svc_type_sel, "Special Service", "Service Type")
                except Exception:
                    pass

            step("save")
            self._prepare_save_payload(page, job, log)
            self._ensure_invoice_checked(page, log)
            self._wait_settled(page, extra_s=0.6)
            self._prepare_save_payload(page, job, log)
            human_pause("action")
            if not self._save_invoice(page, log):
                err_screenshot = self._save_screenshot(page, f"no_save_{job.booking_no}")
                labels = self._visible_form_button_labels(page)
                browser.close()
                raise RuntimeError(
                    f"Could not find the Save button on {page.url}. "
                    f"Visible buttons: {labels or '(none)'}. Screenshot: {err_screenshot}"
                )
            self._wait_settled(page, extra_s=1.5)
            self._confirm_save_or_retry(page, log)

            step("proof")
            proof_path = self._save_screenshot(page, f"proof_{job.booking_no}")
            log(f"Audit screenshot captured: {proof_path}")

            browser.close()
            return proof_path

    # ── Navigation ──────────────────────────────────────────────────────────

    def _navigate_to_special_service_page(self, page, log_func: Callable[[str], None]):
        if self._is_error_page(page):
            log_func("Portal error page detected — reopening Special Service Invoice...")
            try:
                page.goto(ELOGIPARK_SSR_URL, wait_until="domcontentloaded", timeout=15000)
                self._wait_settled(page)
            except Exception as e:
                log_func(f"Reload after error page failed: {e}")

        if self._is_ss_invoice_form(page) and not self._is_error_page(page):
            self._enter_add_mode(page, log_func)
            return

        log_func(f"Opening {ELOGIPARK_SSR_URL} ...")
        try:
            page.goto(ELOGIPARK_SSR_URL, wait_until="domcontentloaded", timeout=15000)
            self._wait_settled(page)
        except Exception as e:
            log_func(f"Direct navigation failed: {e}")

        if self._is_error_page(page) or not self._is_ss_invoice_form(page):
            self._navigate_via_menu(page, log_func)

        if self._login_form_visible(page):
            raise RuntimeError(
                "Navigation returned to the login page. Please log in again, then click Start Bot."
            )

        if self._is_error_page(page) or not self._is_ss_invoice_form(page):
            path = self._save_screenshot(page, "nav_failed")
            raise RuntimeError(
                f"Could not open Special Service Invoice. "
                f"URL={page.url} title={page.title()!r}. Screenshot: {path}"
            )

        self._enter_add_mode(page, log_func)

    def _navigate_via_menu(self, page, log_func: Callable[[str], None]):
        log_func("Navigating via menu: Commercial / Special Service ...")
        try:
            menu = page.query_selector(
                "a[href*='SSInvoice'], a:has-text('Special Service Invoice'), "
                "a:has-text('Special Service')"
            )
            if not menu:
                commercial = page.query_selector("a:has-text('Commercial'), a:has-text('Finance')")
                if commercial:
                    commercial.hover()
                    time.sleep(0.4)
                    commercial.click()
                    time.sleep(0.4)
                menu = page.query_selector(
                    "a[href*='SSInvoice'], a:has-text('Special Service Invoice'), "
                    "a:has-text('Special Service')"
                )
            if menu:
                menu.click()
                page.wait_for_load_state("domcontentloaded")
                self._wait_settled(page)
        except Exception as e:
            log_func(f"Menu navigation note: {e}")

    def _enter_add_mode(self, page, log_func: Callable[[str], None]):
        """Leave a previous invoice if needed, then click ADD to start a new one."""
        if self._form_editable(page):
            return

        labels = [l.upper() for l in self._visible_form_button_labels(page)]
        if "CANCEL" in labels and "ADD" not in labels:
            log_func("Previous invoice still open (Save/Cancel). Clicking Cancel to start a new entry...")
            self._click_form_button(page, ["CANCEL", "Cancel"], log_func)
            self._wait_settled(page, extra_s=1.0)

        if self._form_editable(page):
            return

        clicked = self._click_form_button(page, ["ADD", "Add"], log_func)
        if not clicked:
            clicked = self._click_control(page, SEL_ADD, log_func)
        if not clicked:
            labels = self._visible_form_button_labels(page)
            log_func(f"ADD button not found. Visible buttons: {labels or '(none)'}")

        self._wait_settled(page, extra_s=1.0)
        if self._form_editable(page) or self._wait_form_editable(page, timeout_ms=20000):
            log_func("Special Service form is now in Add mode.")
            return

        labels = self._visible_form_button_labels(page)
        path = self._save_screenshot(page, "form_disabled")
        raise RuntimeError(
            "Special Service form is still disabled after clicking ADD. "
            f"Visible buttons: {labels or '(none)'}. URL={page.url}. Screenshot: {path}"
        )

    def _form_editable(self, page) -> bool:
        """True when Doc Type or Booking No can be filled (Add mode)."""
        for candidates in (SEL_DOC_TYPE, SEL_BOOKING):
            el = self._find_element(page, candidates)
            try:
                if el and el.is_visible() and el.is_enabled():
                    return True
            except Exception:
                continue
        return False

    def _booking_enabled(self, page) -> bool:
        booking = self._find_element(page, SEL_BOOKING)
        try:
            return bool(booking and booking.is_enabled())
        except Exception:
            return False

    def _wait_form_editable(self, page, timeout_ms: int = 15000) -> bool:
        try:
            page.wait_for_function(
                """() => {
                    const nodes = [
                        document.querySelector("select[id*='lstDocType']"),
                        document.querySelector("select[id*='DocType']"),
                        document.querySelector("input[id*='textBookingNo']"),
                    ];
                    return nodes.some(el => el && !el.disabled && el.type !== 'hidden');
                }""",
                timeout=timeout_ms,
            )
            return True
        except Exception:
            return self._form_editable(page)

    def _wait_booking_enabled(self, page, timeout_ms: int = 15000) -> bool:
        try:
            page.wait_for_function(
                """() => {
                    const el = document.querySelector("input[id*='textBookingNo']");
                    return !!(el && !el.disabled && el.type !== 'hidden');
                }""",
                timeout=timeout_ms,
            )
            return True
        except Exception:
            return self._booking_enabled(page)

    def _click_control(self, page, selectors: List[str], log_func: Optional[Callable[[str], None]] = None) -> bool:
        """Click a specific submit control (Playwright user click, then wait for postback)."""
        sel = self._find_selector(page, selectors)
        if not sel:
            return False
        if log_func:
            log_func(f"Clicking {sel}")
        try:
            loc = page.locator(sel).first
            loc.scroll_into_view_if_needed(timeout=3000)
            loc.click(timeout=8000)
        except Exception as e:
            if log_func:
                log_func(f"Locator click failed ({e}); trying DOM click")
            try:
                page.eval_on_selector(sel, "el => el.click()")
            except Exception:
                return False
        try:
            page.wait_for_load_state("domcontentloaded", timeout=20000)
        except Exception:
            pass
        self._wait_settled(page, extra_s=0.8)
        return True

    def _wait_bill_party_ready(self, page) -> None:
        try:
            page.wait_for_function(
                """() => {
                    const sels = [...document.querySelectorAll('select')];
                    const el = sels.find(s => /biito|billparty|partynam|bill.?party/i.test(s.id + ' ' + (s.title||'')));
                    if (!el || el.disabled) return false;
                    return [...el.options].some(o => {
                        const t = (o.text || '').trim();
                        return t && !/^-+select/i.test(t);
                    });
                }""",
                timeout=20000,
            )
        except Exception:
            pass

    def _wait_after_booking_go(self, page) -> None:
        """After Booking GO, Invoice To should enable or an error should appear."""
        try:
            page.wait_for_function(
                """() => {
                    const inv = document.querySelector("select[id*='lstInvoiceTo']");
                    const err = document.querySelector("#ctl00_ContentPlaceHolder1_lblErrorMessage");
                    const cont = document.querySelector("input[id*='textContNo']");
                    if (err && (err.innerText || '').trim()) return true;
                    if (inv && !inv.disabled) return true;
                    if (cont && (cont.value || '').trim().length >= 10) return true;
                    return false;
                }""",
                timeout=20000,
            )
        except Exception:
            pass
        try:
            page.wait_for_function(
                """() => {
                    const inv = document.querySelector("select[id*='lstInvoiceTo']");
                    return !!(inv && !inv.disabled);
                }""",
                timeout=8000,
            )
        except Exception:
            pass

    def _raise_if_portal_error(self, page, context: str) -> None:
        try:
            err = page.inner_text("#ctl00_ContentPlaceHolder1_lblErrorMessage").strip()
        except Exception:
            err = ""
        title = ""
        try:
            title = page.title()
        except Exception:
            pass
        if err:
            path = self._save_screenshot(page, "portal_error")
            raise RuntimeError(f"Portal error {context}: {err}. Screenshot: {path}")
        if "not in a correct format" in title.lower() or self._is_error_page(page):
            path = self._save_screenshot(page, "portal_error")
            raise RuntimeError(f"Portal error {context}: {title or 'server error'}. Screenshot: {path}")

    def _ensure_invoice_checked(self, page, log_func: Callable[[str], None]) -> None:
        """Portal rejects Save unless 'Invoice Checked' is ticked."""
        sel = self._find_selector(page, SEL_INVOICE_CHECKED)
        try:
            already = bool(sel and page.is_checked(sel))
        except Exception:
            already = False
        if already:
            log_func("Invoice Checked is already ticked.")
            return

        log_func("Ticking 'Invoice Checked' before Save...")
        clicked = False
        try:
            page.locator("label:has-text('Invoice Checked')").first.click(timeout=4000)
            clicked = True
        except Exception:
            pass
        if sel and not clicked:
            try:
                page.locator(sel).click(timeout=4000, force=True)
                clicked = True
            except Exception:
                pass
        if not clicked:
            page.evaluate(
                """() => {
                    const el = document.querySelector("input[id*='chkInvoiceChecked'], input[id*='InvoiceChecked']");
                    if (!el) return;
                    el.checked = true;
                    el.dispatchEvent(new Event('click', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }"""
            )

        try:
            if sel and not page.is_checked(sel):
                page.check(sel, force=True)
        except Exception:
            pass

    def _save_invoice(self, page, log_func: Callable[[str], None]) -> bool:
        if self._click_control(page, SEL_SAVE, log_func):
            return True
        return self._click_form_button(page, ["SAVE", "Save"], log_func)

    def _prepare_save_payload(self, page, job: InvoiceJob, log_func: Callable[[str], None]) -> None:
        """
        SSInvoice.aspx.vb line 344 does:
            TaxOnAmt = ((BillRate * BillQnty) / 100) * hdnTaxOnPercentage.Value
        An empty string there throws FormatException on Save.
        """
        log_func("Filling blank qty/rate/tax fields so Save is numeric...")
        try:
            filled = page.evaluate(
                """(rate) => {
                    const setIfBlank = (el, val) => {
                        if (!el) return false;
                        if (!(el.value || '').trim()) {
                            el.value = val;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                        return false;
                    };
                    const zeroBlanks = (selector) => {
                        document.querySelectorAll(selector).forEach(el => setIfBlank(el, '0'));
                    };
                    zeroBlanks("input[id*='TaxOnPercentage'], input[id*='hdnTax'], input[id*='TaxPerc']");
                    zeroBlanks("input[id*='textServiceTax'], input[id*='TextSBT'], input[id*='textEducTax']");
                    zeroBlanks("input[id*='textTaxAmount'], input[id*='textAmount'], input[id*='textTotalAmount']");
                    zeroBlanks("input[id*='textRep'], input[id*='textWeiver']");

                    const headerTax = document.querySelector("input[id*='TaxOnPercentage']");
                    const rowTax = document.querySelector("input[id*='hdnTaxPerc']");
                    if (headerTax && !(headerTax.value || '').trim()) {
                        headerTax.value = ((rowTax && (rowTax.value || '').trim()) || '0');
                    }

                    let ratesFilled = 0;
                    document.querySelectorAll("input[id*='chkSelect']").forEach(chk => {
                        if (!chk.checked) return;
                        const base = (chk.id || '').replace(/chkSelect$/, '');
                        const qty = document.getElementById(base + 'textQuntity');
                        const rateEl = document.getElementById(base + 'textRate');
                        if (qty && !(qty.value || '').trim()) qty.value = '1';
                        if (rateEl && !(rateEl.value || '').trim()) {
                            rateEl.value = String(rate);
                            ratesFilled += 1;
                        }
                        if (rateEl) {
                            rateEl.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        if (typeof SelectAmount === 'function') {
                            try { SelectAmount(chk); } catch (e) {}
                        }
                    });
                    return {
                        tax: (headerTax && headerTax.value) || '',
                        ratesFilled
                    };
                }""",
                job.rate,
            )
            log_func(f"Pre-save numeric check: tax%={filled.get('tax')!r}, empty rates filled={filled.get('ratesFilled')}")
        except Exception as e:
            log_func(f"Pre-save numeric fill note: {e}")

    def _confirm_save_or_retry(self, page, log_func: Callable[[str], None]) -> None:
        title = ""
        body = ""
        try:
            title = page.title()
        except Exception:
            pass
        try:
            body = page.inner_text("body")[:800]
        except Exception:
            pass
        if is_aspnet_error_page(title, body):
            path = self._save_screenshot(page, "save_format_error")
            try:
                page.goto(ELOGIPARK_SSR_URL, wait_until="domcontentloaded", timeout=15000)
                self._wait_settled(page)
            except Exception:
                pass
            raise RuntimeError(
                "Portal threw FormatException on Save (empty tax percentage or rate). "
                f"Reopened Special Service Invoice. Screenshot: {path}"
            )

        err = ""
        try:
            err = page.inner_text("#ctl00_ContentPlaceHolder1_lblErrorMessage").strip()
        except Exception:
            pass
        if not err:
            return
        log_func(f"Portal message after Save: {err}")
        if is_portal_success_message(err):
            log_func(f"Save confirmed by portal: {err}")
            return
        if "check" in err.lower() and "invoice" in err.lower():
            self._ensure_invoice_checked(page, log_func)
            if not self._save_invoice(page, log_func):
                raise RuntimeError(f"Portal requires Invoice Checked, and Save could not be clicked. {err}")
            self._wait_settled(page, extra_s=1.5)
            try:
                title2 = page.title()
                body2 = page.inner_text("body")[:500]
            except Exception:
                title2, body2 = "", ""
            if is_aspnet_error_page(title2, body2):
                path = self._save_screenshot(page, "save_format_error")
                try:
                    page.goto(ELOGIPARK_SSR_URL, wait_until="domcontentloaded", timeout=15000)
                except Exception:
                    pass
                raise RuntimeError(
                    "Portal threw FormatException on Save retry. "
                    f"Screenshot: {path}"
                )
            try:
                err2 = page.inner_text("#ctl00_ContentPlaceHolder1_lblErrorMessage").strip()
            except Exception:
                err2 = ""
            if not err2 or is_portal_success_message(err2):
                if err2:
                    log_func(f"Save confirmed by portal: {err2}")
                return
            path = self._save_screenshot(page, "save_rejected")
            raise RuntimeError(f"Portal rejected Save: {err2}. Screenshot: {path}")
        path = self._save_screenshot(page, "save_rejected")
        raise RuntimeError(f"Portal rejected Save: {err}. Screenshot: {path}")

    def _fill_enabled(self, page, selector: str, value: str, field_name: str) -> None:
        try:
            page.wait_for_function(
                """(sel) => {
                    const el = document.querySelector(sel);
                    return !!(el && !el.disabled);
                }""",
                arg=selector,
                timeout=10000,
            )
        except Exception:
            pass
        try:
            page.fill(selector, value)
        except Exception as e:
            raise RuntimeError(f"Could not fill {field_name} on {page.url}: {e}") from e

    def _find_named_button(self, page, names: List[str]) -> Optional[dict]:
        """Locate a visible ASP.NET button by its value/text. Returns id/name/label."""
        try:
            return page.evaluate(
                """(wanted) => {
                    const wantedSet = new Set(wanted.map(n => (n || '').toUpperCase()));
                    const nodes = [...document.querySelectorAll(
                        "input[type=submit], input[type=button], button, a.FormButton"
                    )];
                    for (const b of nodes) {
                        const style = window.getComputedStyle(b);
                        if (style.display === 'none' || style.visibility === 'hidden') continue;
                        if (b.offsetParent === null && b.tagName !== 'A') continue;
                        const label = ((b.value || b.innerText || b.textContent || '') + '').trim();
                        if (!label || !wantedSet.has(label.toUpperCase())) continue;
                        return {
                            found: true,
                            id: b.id || '',
                            name: b.getAttribute('name') || '',
                            label,
                            type: b.type || b.tagName,
                            href: b.getAttribute('href') || '',
                        };
                    }
                    return { found: false };
                }""",
                list(names),
            )
        except Exception:
            return None

    def _aspnet_postback(self, page, name: str, btn_id: str) -> str:
        """
        Submit the ASP.NET form as the named button.

        Default Button controls are input[type=submit]; the server only handles
        the click if that button is the submitter. Wrapping __doPostBack in
        expect_navigation also destroys the CDP execution context, so the submit
        is scheduled on a timer and we wait for load afterwards.
        """
        return page.evaluate(
            """({ name, id }) => {
                const el = (id && document.getElementById(id))
                    || (name && document.getElementsByName(name)[0]);
                if (!el) return 'missing';
                try { el.scrollIntoView({block: 'center', inline: 'nearest'}); } catch (e) {}
                const form = el.form
                    || document.getElementById('aspnetForm')
                    || document.getElementById('form1')
                    || document.forms[0];
                const href = el.getAttribute && (el.getAttribute('href') || '');
                const isLinkPost = (el.tagName === 'A') || (href && href.indexOf('__doPostBack') >= 0);
                window.setTimeout(() => {
                    if (isLinkPost && typeof __doPostBack === 'function' && name) {
                        __doPostBack(name, '');
                        return;
                    }
                    if (form && typeof form.requestSubmit === 'function' && el.tagName === 'INPUT') {
                        form.requestSubmit(el);
                        return;
                    }
                    if (el.click) el.click();
                }, 50);
                return isLinkPost ? 'scheduled-dopostback' : 'scheduled-submit';
            }""",
            {"name": name, "id": btn_id},
        )

    def _click_form_button(self, page, names: List[str], log_func: Optional[Callable[[str], None]] = None) -> bool:
        """Activate a visible ASP.NET button without crashing the CDP session."""
        info = self._find_named_button(page, names) or {}
        if not info.get("found"):
            return False

        btn_id = info.get("id") or ""
        name = info.get("name") or ""
        label = info.get("label") or names[0]
        if log_func:
            log_func(
                f"Clicking form button '{label}' (id={btn_id or 'n/a'}, name={name or 'n/a'})"
            )

        if btn_id:
            try:
                page.locator(f"#{btn_id}").scroll_into_view_if_needed(timeout=3000)
            except Exception:
                pass

        try:
            result = self._aspnet_postback(page, name, btn_id)
            if log_func:
                log_func(f"Button activate method: {result}")
        except Exception as e:
            if log_func:
                log_func(f"Scheduled submit failed ({e}); trying Playwright click")
            if btn_id:
                try:
                    page.click(f"#{btn_id}", timeout=8000, no_wait_after=True)
                except Exception as e2:
                    if log_func:
                        log_func(f"Playwright click failed: {e2}")
                    return False

        try:
            page.wait_for_load_state("domcontentloaded", timeout=20000)
        except Exception:
            pass
        self._wait_settled(page, extra_s=0.8)
        return True

    def _visible_form_button_labels(self, page) -> List[str]:
        labels: List[str] = []
        locators = page.locator("input[type='submit'], input[type='button'], button")
        try:
            count = locators.count()
        except Exception:
            return labels
        for i in range(count):
            el = locators.nth(i)
            try:
                if not el.is_visible():
                    continue
                label = (el.get_attribute("value") or el.inner_text() or "").strip()
                if label:
                    labels.append(label)
            except Exception:
                continue
        return labels

    # ── Container grid ──────────────────────────────────────────────────────

    def _match_and_fill_container_rows(
        self, page, job: InvoiceJob, log_func: Callable[[str], None]
    ) -> List[str]:
        matched: List[str] = []
        targets = {c.strip().upper(): c for c in job.containers}

        inputs = page.query_selector_all("input[id*='textContNo']")
        if not inputs:
            # Fallback: row text scan, but only inside the invoice repeater if present.
            grid = page.query_selector(
                "table[id*='rcInvoiceDetails'], table[id*='InvoiceDetails'], "
                "table[id*='grd'], table[id*='Grid']"
            )
            rows = grid.query_selector_all("tr") if grid else []
            for row in rows:
                row_text = (row.inner_text() or "").upper()
                for target_up, original in list(targets.items()):
                    if target_up in row_text:
                        checkbox = row.query_selector("input[type='checkbox']")
                        if checkbox and not checkbox.is_checked():
                            checkbox.check()
                        if original not in matched:
                            matched.append(original)
                            log_func(f"Checked container: {original}")
            return matched

        for inp in inputs:
            value = (inp.input_value() or "").strip().upper()
            if not value:
                continue
            hit = None
            for target_up, original in targets.items():
                if target_up == value or target_up in value:
                    hit = original
                    break
            if not hit:
                continue

            elem_id = inp.get_attribute("id") or ""
            base = elem_id[: -len("textContNo")] if elem_id.endswith("textContNo") else ""
            if base:
                chk = page.query_selector(f"#{base}chkSelect")
                if chk and not chk.is_checked():
                    chk.check()
                    self._wait_settled(page, extra_s=0.4)
                svc = page.query_selector(f"#{base}lstService")
                if svc:
                    self._select_dropdown(page, f"#{base}lstService", job.service, f"Service ({hit})")
                    self._wait_settled(page, extra_s=0.6)
                qty = page.query_selector(f"#{base}textQuntity")
                if qty:
                    try:
                        qty.fill("1")
                    except Exception:
                        pass
                rate = page.query_selector(f"#{base}textRate")
                if rate:
                    try:
                        rate.fill(str(job.rate))
                    except Exception:
                        page.fill(f"#{base}textRate", str(job.rate), force=True)
            else:
                checkbox = inp.evaluate_handle(
                    "el => el.closest('tr')?.querySelector(\"input[type='checkbox']\")"
                )
                if checkbox:
                    try:
                        checkbox.as_element().check()
                    except Exception:
                        pass

            if hit not in matched:
                matched.append(hit)
                log_func(f"Checked container: {hit} (service={job.service}, rate={job.rate})")

        return matched

    def _read_container_values(self, page) -> List[str]:
        values = []
        for inp in page.query_selector_all("input[id*='textContNo']"):
            val = (inp.input_value() or "").strip()
            if val:
                values.append(val)
        return values

    def _wait_for_container_values(self, page, timeout_ms: int = 15000) -> None:
        try:
            page.wait_for_function(
                """() => [...document.querySelectorAll("input[id*='textContNo']")]
                    .some(i => (i.value || '').trim().length >= 10)""",
                timeout=timeout_ms,
            )
        except Exception:
            pass

    # ── Page classification ─────────────────────────────────────────────────

    def _assert_portal_ok(self, page, step: str, booking_no: str) -> None:
        """Fail fast with a typed error so the worker can pause and resume."""
        try:
            closed = page.is_closed()
        except Exception:
            closed = True
        if closed:
            raise SessionNotFoundError(
                "The eLOGiPark tab was closed. Re-open the portal, log in, then click Start Bot to resume.",
                step=step,
                booking_no=booking_no,
            )
        if self._login_form_visible(page):
            raise LoginRequiredError(
                "Portal session expired or is on the login page. Log in, then click Start Bot to resume.",
                step=step,
                booking_no=booking_no,
            )
        if self._is_error_page(page):
            title = ""
            try:
                title = page.title()
            except Exception:
                pass
            raise WebsiteUnavailableError(
                f"eLOGiPark returned an application error ({title or 'unknown'}). "
                "The current booking was not marked complete. Restore the portal and click Start Bot to resume.",
                step=step,
                booking_no=booking_no,
            )

    def _is_error_page(self, page) -> bool:
        try:
            title = page.title()
        except Exception:
            title = ""
        body = ""
        try:
            body = page.inner_text("body")[:500]
        except Exception:
            pass
        return is_aspnet_error_page(title, body)

    def _is_ss_invoice_form(self, page) -> bool:
        if self._is_error_page(page):
            return False
        url = page.url.lower()
        if "ssinvoice" in url:
            return True
        return bool(
            page.query_selector(
                "select[id*='lstDocType'], input[id*='textBookingNo'], "
                "select[id*='DocType'], input[id*='Booking']"
            )
        )

    def _login_form_visible(self, page) -> bool:
        try:
            user = page.query_selector("input#textUserName")
            pwd = page.query_selector("input#textPassword")
            return bool(user and pwd and user.is_visible())
        except Exception:
            return False

    def _otp_form_visible(self, page) -> bool:
        try:
            otp = page.query_selector(SEL_OTP)
            return bool(otp and otp.is_visible())
        except Exception:
            return False

    def _logged_in_user(self, page) -> str:
        try:
            el = page.query_selector("#ctl00_lblLoginUser, #lblLoginUser")
            if el:
                text = (el.inner_text() or "").strip()
                if text:
                    return text
        except Exception:
            pass
        return ""

    # ── Selector helpers ────────────────────────────────────────────────────

    def _find_selector(self, page, candidates: List[str]) -> Optional[str]:
        for sel in candidates:
            try:
                elem = page.query_selector(sel)
                if elem:
                    return sel
            except Exception:
                pass
        return None

    def _find_element(self, page, candidates: List[str]):
        sel = self._find_selector(page, candidates)
        if not sel:
            return None
        try:
            return page.query_selector(sel)
        except Exception:
            return None

    def _require_selector(self, page, candidates: List[str], field_name: str) -> str:
        sel = self._find_selector(page, candidates)
        if not sel:
            for _ in range(4):
                self._wait_settled(page, extra_s=0.5)
                sel = self._find_selector(page, candidates)
                if sel:
                    break
        if not sel:
            available = []
            try:
                available = page.eval_on_selector_all(
                    "select",
                    "els => els.map(e => e.id || e.name || e.title).filter(Boolean)",
                )
            except Exception:
                pass
            path = self._save_screenshot(page, f"missing_{field_name.replace(' ', '_')}")
            raise RuntimeError(
                f"Could not find {field_name} on {page.url} (title={page.title()!r}). "
                f"Selects on page: {available or '(none)'}. Screenshot: {path}"
            )
        return sel

    def _select_dropdown(self, page, selector: str, desired: str, field_name: str) -> None:
        desired_clean = (desired or "").strip()
        if not desired_clean:
            raise RuntimeError(f"{field_name} value is empty.")

        try:
            page.wait_for_function(
                """(sel) => { const el = document.querySelector(sel); return !!(el && !el.disabled); }""",
                arg=selector,
                timeout=15000,
            )
        except Exception:
            pass

        try:
            page.select_option(selector, value=desired_clean)
            return
        except Exception:
            pass
        try:
            page.select_option(selector, label=desired_clean)
            return
        except Exception:
            pass

        try:
            options = page.eval_on_selector_all(
                f"{selector} option",
                "els => els.map(e => ({value: e.value, label: (e.textContent || '').trim()}))",
            )
        except Exception:
            options = []

        desired_up = desired_clean.upper()
        match = None
        for opt in options or []:
            label = (opt.get("label") or "").strip()
            value = (opt.get("value") or "").strip()
            if label.upper() == desired_up or value.upper() == desired_up:
                match = opt
                break
        if match is None:
            for opt in options or []:
                label = (opt.get("label") or "").strip()
                value = (opt.get("value") or "").strip()
                if desired_up in label.upper() or desired_up in value.upper():
                    match = opt
                    break
        if match is None:
            for opt in options or []:
                label = (opt.get("label") or "").strip()
                if label and label.upper() in desired_up:
                    match = opt
                    break

        if match is None:
            available = ", ".join(
                f"{o.get('label') or o.get('value')}" for o in (options or [])[:12]
            ) or "(none)"
            raise RuntimeError(
                f"Could not select {field_name}={desired_clean!r}. Available: {available}"
            )

        try:
            page.select_option(selector, value=match.get("value") or "")
        except Exception:
            page.select_option(selector, label=match.get("label") or desired_clean)

    def _wait_settled(self, page, extra_s: float = 0.6) -> None:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        human_pause("action", min_seconds=min(extra_s, 0.4))
        if extra_s > 1.2:
            time.sleep(extra_s - 1.2)

    def _find_or_create_portal_page(self, context, default_url: str = ELOGIPARK_LOGIN_URL):
        for p in reversed(context.pages):
            if not p.is_closed() and "kribhcoinfra" in p.url.lower():
                return p
        if context.pages:
            p = context.pages[-1]
            p.goto(default_url)
            return p
        return context.new_page()

    def _save_screenshot(self, page, context_name: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{context_name}_{timestamp}.png"
        filepath = COMPLETED_DIR / filename
        try:
            page.screenshot(path=str(filepath), full_page=True)
            return str(filepath)
        except Exception:
            return ""

    def capture_screenshot(self, context_name: str) -> str:
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(CDP_URL, timeout=3000)
                context = browser.contexts[0]
                page = None
                for candidate in reversed(context.pages):
                    if not candidate.is_closed() and "kribhcoinfra" in candidate.url.lower():
                        page = candidate
                        break
                if page is None and context.pages:
                    page = context.pages[0]
                path = self._save_screenshot(page, context_name) if page else ""
                browser.close()
                return path
        except Exception:
            return ""

    def cleanup(self) -> None:
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None
