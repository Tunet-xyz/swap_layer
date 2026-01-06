"""
Payment infrastructure module.
Provides an abstraction layer for payment and subscription providers.
"""

from .factory import get_payment_provider
from .adapter import PaymentProviderAdapter

# Convenience alias
get_provider = get_payment_provider

__all__ = [
    'get_provider',
    'get_payment_provider',
    'PaymentProviderAdapter',
]
