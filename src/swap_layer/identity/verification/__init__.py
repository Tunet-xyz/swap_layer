"""
Identity verification infrastructure module.
Provides an abstraction layer for identity verification providers (Stripe, Onfido, etc.).
"""

from .factory import get_identity_verification_provider
from .adapter import IdentityVerificationProviderAdapter

# Convenience alias
get_provider = get_identity_verification_provider

__all__ = [
    'get_provider',
    'get_identity_verification_provider',
    'IdentityVerificationProviderAdapter',
]
