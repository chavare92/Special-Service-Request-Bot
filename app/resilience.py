"""Bounded retries, timeouts, and human-like delays."""
import random
import time
from typing import Callable, Optional, TypeVar

from app.config import (
    HUMAN_DELAY_ACTION_SEC,
    HUMAN_DELAY_BETWEEN_JOBS_SEC,
    HUMAN_DELAY_NAV_SEC,
    MAX_ACTION_RETRIES,
    RETRY_BACKOFF_SEC,
)
from app.errors import (
    LoginRequiredError,
    RetryExhaustedError,
    SessionNotFoundError,
    WebsiteUnavailableError,
)

T = TypeVar("T")

_DELAYS = {
    "action": HUMAN_DELAY_ACTION_SEC,
    "nav": HUMAN_DELAY_NAV_SEC,
    "job": HUMAN_DELAY_BETWEEN_JOBS_SEC,
}


def human_pause(kind: str = "action", min_seconds: float = 0.0) -> None:
    """Sleep a random interval so portal actions are not instantaneous."""
    lo, hi = _DELAYS.get(kind, HUMAN_DELAY_ACTION_SEC)
    lo = max(float(lo), float(min_seconds))
    hi = max(float(hi), lo)
    time.sleep(random.uniform(lo, hi))


def retry_call(
    fn: Callable[[], T],
    *,
    attempts: int = MAX_ACTION_RETRIES,
    description: str = "action",
    abort_check: Optional[Callable[[], bool]] = None,
    on_retry: Optional[Callable[[int, BaseException], None]] = None,
) -> T:
    """
    Run fn up to `attempts` times. Login/session/outage errors are not retried.
    Always terminates — never loops forever.
    """
    attempts = max(1, int(attempts))
    last: Optional[BaseException] = None
    for attempt in range(1, attempts + 1):
        if abort_check and abort_check():
            raise RetryExhaustedError(
                "Cancelled before retry completed.",
                step=description,
                retry_count=attempt - 1,
            )
        try:
            return fn()
        except (LoginRequiredError, SessionNotFoundError, WebsiteUnavailableError):
            raise
        except RetryExhaustedError:
            raise
        except Exception as e:
            last = e
            if attempt >= attempts:
                break
            if on_retry:
                on_retry(attempt, e)
            backoff_lo, backoff_hi = RETRY_BACKOFF_SEC
            time.sleep(random.uniform(backoff_lo, backoff_hi) * attempt)
    raise RetryExhaustedError(
        f"{description} failed after {attempts} attempt(s): {last}",
        step=description,
        retry_count=attempts,
    ) from last
