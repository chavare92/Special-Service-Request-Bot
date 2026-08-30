"""Typed errors and failure categories for SSR bot recovery."""
from enum import Enum


class ErrorCategory(str, Enum):
    WEBSITE_UNAVAILABLE = "Website Unavailable"
    LOGIN_REQUIRED = "Login Required"
    SESSION_NOT_FOUND = "Website Session Not Found"
    TIMEOUT = "Timeout"
    ELEMENT_NOT_FOUND = "Element Not Found"
    APPLICATION_ERROR = "Application Error"
    UNEXPECTED_ERROR = "Unexpected Error"
    VALIDATION_ERROR = "Validation Error"
    CANCELLED = "Cancelled"


class SSRBotError(Exception):
    """Base recoverable automation error."""

    def __init__(
        self,
        message: str,
        *,
        category: ErrorCategory = ErrorCategory.UNEXPECTED_ERROR,
        step: str = "",
        booking_no: str = "",
        retry_count: int = 0,
        process_name: str = "SSR Invoicing",
    ):
        super().__init__(message)
        self.category = category
        self.step = step
        self.booking_no = booking_no
        self.retry_count = retry_count
        self.process_name = process_name

    def log_fields(self) -> dict:
        return {
            "category": self.category.value,
            "process": self.process_name,
            "step": self.step,
            "record": self.booking_no,
            "retry": self.retry_count,
            "error": str(self),
        }


class LoginRequiredError(SSRBotError):
    def __init__(self, message: str = "Portal login is required.", **kwargs):
        kwargs.setdefault("category", ErrorCategory.LOGIN_REQUIRED)
        super().__init__(message, **kwargs)


class SessionNotFoundError(SSRBotError):
    def __init__(self, message: str = "Browser session was not found.", **kwargs):
        kwargs.setdefault("category", ErrorCategory.SESSION_NOT_FOUND)
        super().__init__(message, **kwargs)


class WebsiteUnavailableError(SSRBotError):
    def __init__(self, message: str = "eLOGiPark is unavailable.", **kwargs):
        kwargs.setdefault("category", ErrorCategory.WEBSITE_UNAVAILABLE)
        super().__init__(message, **kwargs)


class RetryExhaustedError(SSRBotError):
    def __init__(self, message: str = "Retry limit reached.", **kwargs):
        kwargs.setdefault("category", ErrorCategory.UNEXPECTED_ERROR)
        super().__init__(message, **kwargs)


def classify_exception(exc: BaseException) -> ErrorCategory:
    if isinstance(exc, SSRBotError):
        return exc.category
    msg = str(exc).lower()
    if "login" in msg or "otp" in msg or "not logged in" in msg:
        return ErrorCategory.LOGIN_REQUIRED
    if "timeout" in msg or "timed out" in msg:
        return ErrorCategory.TIMEOUT
    if "could not find" in msg or "not found" in msg or "no_save" in msg:
        return ErrorCategory.ELEMENT_NOT_FOUND
    if "formatexception" in msg or "server error" in msg or "not in a correct format" in msg:
        return ErrorCategory.APPLICATION_ERROR
    if "browser" in msg and ("not" in msg or "cdp" in msg or "connect" in msg):
        return ErrorCategory.SESSION_NOT_FOUND
    if "unavailable" in msg or "net::" in msg or "connection" in msg:
        return ErrorCategory.WEBSITE_UNAVAILABLE
    return ErrorCategory.UNEXPECTED_ERROR


def is_pause_and_wait_error(exc: BaseException) -> bool:
    """True when the user or website must recover before the batch can continue."""
    cat = classify_exception(exc)
    return cat in (
        ErrorCategory.LOGIN_REQUIRED,
        ErrorCategory.SESSION_NOT_FOUND,
        ErrorCategory.WEBSITE_UNAVAILABLE,
    )
