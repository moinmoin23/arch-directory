"""Reusable rate limiting and retry with exponential backoff."""

import functools
import logging
import time

import httpx

logger = logging.getLogger(__name__)

# HTTP status codes that should trigger a retry
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def retry_with_backoff(
    max_attempts: int = 3,
    backoff_base: float = 2.0,
    max_backoff: float = 60.0,
    retryable_exceptions: tuple = (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout),
):
    """Decorator that retries a function with exponential backoff.

    Retries on specified exceptions and on HTTP responses with retryable status codes.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(*args, **kwargs)
                    # If the result is an httpx.Response, check status
                    if isinstance(result, httpx.Response) and result.status_code in RETRYABLE_STATUS:
                        wait = min(backoff_base ** attempt, max_backoff)
                        logger.warning(
                            "Retryable status %d from %s (attempt %d/%d), waiting %.1fs",
                            result.status_code, func.__name__, attempt, max_attempts, wait,
                        )
                        if attempt < max_attempts:
                            time.sleep(wait)
                            continue
                    return result
                except retryable_exceptions as e:
                    last_exception = e
                    wait = min(backoff_base ** attempt, max_backoff)
                    logger.warning(
                        "%s in %s (attempt %d/%d), waiting %.1fs: %s",
                        type(e).__name__, func.__name__, attempt, max_attempts, wait, e,
                    )
                    if attempt < max_attempts:
                        time.sleep(wait)
            # All attempts exhausted
            if last_exception:
                raise last_exception
            return result  # type: ignore[possibly-undefined]
        return wrapper
    return decorator


class RateLimiter:
    """Simple rate limiter that enforces a minimum delay between calls."""

    def __init__(self, min_delay: float = 1.0):
        self.min_delay = min_delay
        self._last_call: float = 0.0

    def wait(self) -> None:
        """Block until enough time has passed since the last call."""
        now = time.monotonic()
        elapsed = now - self._last_call
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self._last_call = time.monotonic()
