from __future__ import annotations

import httpx


RETRYABLE_HTTP_STATUS_CODES = {
    408,
    429,
    500,
    502,
    503,
    504,
}


def is_retryable_http_error(
    error: Exception,
) -> bool:
    """Return whether an HTTP failure may be temporary."""

    if isinstance(
        error,
        httpx.TransportError,
    ):
        return True

    if isinstance(
        error,
        httpx.HTTPStatusError,
    ):
        return error.response.status_code in RETRYABLE_HTTP_STATUS_CODES

    return False


def retry_delay(
    base_delay_seconds: float,
    failed_attempt: int,
) -> float:
    """Calculate exponential backoff after a failed attempt."""

    return base_delay_seconds * (2 ** (failed_attempt - 1))
