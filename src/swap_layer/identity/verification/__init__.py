"""
Identity verification infrastructure module.
Provides an abstraction layer for identity verification providers (Stripe, Onfido, etc.).
"""

from .factory import get_identity_verification_provider
from .adapter import IdentityVerificationProviderAdapter
from .services import VerificationService
from .models import (
    IdentityVerificationSession,
    AbstractIdentityVerificationSession,
    IdentityVerificationMixin,
    KYCStatusMixin
)

# Convenience alias
get_provider = get_identity_verification_provider

__all__ = [
    'get_provider',
    'get_identity_verification_provider',
    'IdentityVerificationProviderAdapter',
    'VerificationService',
    'IdentityVerificationSession',
    'AbstractIdentityVerificationSession',
    'IdentityVerificationMixin',
    'KYCStatusMixin',
]
