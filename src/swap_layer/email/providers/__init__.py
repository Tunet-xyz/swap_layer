"""
Email Provider Implementations

This package contains concrete implementations of the EmailProviderAdapter
for different email service providers.
"""
from .smtp import SMTPEmailProvider
from .django_email import DjangoEmailAdapter

__all__ = [
    'SMTPEmailProvider',
    'DjangoEmailAdapter',
]
