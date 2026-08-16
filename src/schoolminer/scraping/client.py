import httpx

from schoolminer.config import DEFAULT_TIMEOUT_SECONDS, USER_AGENT


def build_client(*, verify: bool = True) -> httpx.Client:
    """Create the HTTP client used to communicate with directory sources."""

    return httpx.Client(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
        timeout=DEFAULT_TIMEOUT_SECONDS,
        follow_redirects=True,
        verify=verify,
    )
