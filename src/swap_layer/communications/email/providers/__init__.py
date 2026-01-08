"""
Email Provider Implementations

This package contains concrete implementations of the EmailProviderAdapter
for different email service providers.
"""

from .django_email import DjangoEmailAdapter
from .smtp import SMTPEmailProvider

__all__ = [
    "SMTPEmailProvider",
    "DjangoEmailAdapter",
]
