"""
Payment infrastructure module.
Provides an abstraction layer for payment and subscription providers.
"""

from .adapter import PaymentProviderAdapter
from .factory import get_payment_provider

# Convenience alias
get_provider = get_payment_provider

__all__ = [
    "get_provider",
    "get_payment_provider",
    "PaymentProviderAdapter",
]
