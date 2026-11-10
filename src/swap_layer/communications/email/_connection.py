"""Django email connections with a finite network timeout."""

from typing import Any

from swap_layer.http import DEFAULT_TIMEOUT


def default_email_connection() -> Any:
    """
    Return Django's default email connection with a bounded SMTP timeout.

    Django's SMTP backend waits indefinitely when no timeout is configured
    (``EMAIL_TIMEOUT``, or the mailer's ``timeout`` option). SwapLayer then uses
    ``DEFAULT_TIMEOUT`` seconds instead. A configured timeout, and backends
    without a ``timeout`` attribute, are left unchanged.
    """
    connection: Any
    try:
        from django.core.mail import mailers  # type: ignore[attr-defined]  # Django 6.1+
    except ImportError:
        from django.core.mail import get_connection

        connection = get_connection()
    else:
        connection = mailers.default
    if getattr(connection, "timeout", DEFAULT_TIMEOUT) is None:
        connection.timeout = DEFAULT_TIMEOUT
    return connection
