"""
HTTP utilities with retry logic for SwapLayer.

Provides resilient HTTP requests with exponential backoff for all provider integrations.
"""

import logging
from functools import wraps

import requests
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    Timeout,
)

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF = 2  # exponential backoff multiplier

# HTTP status codes that should trigger a retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Exceptions that should trigger a retry
RETRYABLE_EXCEPTIONS = (ConnectionError, Timeout)


def is_retryable_error(exception: Exception) -> bool:
    """Check if an exception should trigger a retry."""
    if isinstance(exception, RETRYABLE_EXCEPTIONS):
        return True
    if isinstance(exception, HTTPError):
        return exception.response.status_code in RETRYABLE_STATUS_CODES
    return False


try:
    from tenacity import (
        before_sleep_log,
        retry,
        retry_if_exception,
        stop_after_attempt,
        wait_exponential,
    )

    TENACITY_AVAILABLE = True

    def create_retry_decorator(
        max_retries: int = DEFAULT_MAX_RETRIES,
        min_wait: float = 1,
        max_wait: float = 60,
    ):
        """
        Create a retry decorator with exponential backoff.

        Args:
            max_retries: Maximum number of retry attempts
            min_wait: Minimum wait time between retries (seconds)
            max_wait: Maximum wait time between retries (seconds)

        Returns:
            Configured retry decorator
        """
        return retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception(is_retryable_error),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )

    # Default retry decorator
    with_retry = create_retry_decorator()

except ImportError:
    TENACITY_AVAILABLE = False

    def create_retry_decorator(
        max_retries: int = DEFAULT_MAX_RETRIES,
        min_wait: float = 1,
        max_wait: float = 60,
    ):
        """Fallback when tenacity is not installed - no retry logic."""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def with_retry(func):
        """Fallback decorator when tenacity is not installed."""
        return func


class ResilientSession:
    """
    A requests session with built-in retry logic and timeouts.

    Use this for all HTTP requests to external providers to ensure
    resilient communication with automatic retries on transient failures.

    Example:
        session = ResilientSession(base_url="https://api.provider.com")
        response = session.get("/users", params={"limit": 10})
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        headers: dict | None = None,
    ):
        """
        Initialize resilient session.

        Args:
            base_url: Base URL for all requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            headers: Default headers for all requests
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()

        if headers:
            self.session.headers.update(headers)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> requests.Response:
        """
        Make an HTTP request with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint (will be appended to base_url)
            **kwargs: Additional arguments passed to requests

        Returns:
            Response object

        Raises:
            RequestException: If all retries fail
        """
        url = f"{self.base_url}{endpoint}" if self.base_url else endpoint
        kwargs.setdefault("timeout", self.timeout)

        @create_retry_decorator(max_retries=self.max_retries)
        def _request():
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response

        return _request()

    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """Make a GET request."""
        return self._make_request("GET", endpoint, **kwargs)

    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """Make a POST request."""
        return self._make_request("POST", endpoint, **kwargs)

    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """Make a PUT request."""
        return self._make_request("PUT", endpoint, **kwargs)

    def patch(self, endpoint: str, **kwargs) -> requests.Response:
        """Make a PATCH request."""
        return self._make_request("PATCH", endpoint, **kwargs)

    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """Make a DELETE request."""
        return self._make_request("DELETE", endpoint, **kwargs)

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def resilient_request(
    method: str,
    url: str,
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    **kwargs,
) -> requests.Response:
    """
    Make a single resilient HTTP request with retry logic.

    Use this for one-off requests. For multiple requests to the same
    service, use ResilientSession instead.

    Args:
        method: HTTP method
        url: Full URL
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        **kwargs: Additional arguments passed to requests

    Returns:
        Response object
    """
    kwargs.setdefault("timeout", timeout)

    @create_retry_decorator(max_retries=max_retries)
    def _request():
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    return _request()
