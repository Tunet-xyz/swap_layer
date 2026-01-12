"""
Email Infrastructure

This module provides an abstraction layer for email providers, allowing the
application to switch between different email services (SMTP, SendGrid, Mailgun,
AWS SES, etc.) without modifying business logic.
"""

from .adapter import EmailProviderAdapter
from .factory import get_email_provider

# Convenience alias
get_provider = get_email_provider

__all__ = [
    "get_provider",
    "get_email_provider",
    "EmailProviderAdapter",
]
