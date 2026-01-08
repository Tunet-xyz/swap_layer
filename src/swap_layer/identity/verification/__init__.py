"""
Identity verification infrastructure module.
Provides an abstraction layer for identity verification providers (Stripe, Onfido, etc.).
"""

from .adapter import IdentityVerificationProviderAdapter
from .factory import get_identity_verification_provider
from .models import (
    AbstractIdentityVerificationSession,
    IdentityVerificationMixin,
    KYCStatusMixin,
    VerificationSessionCreate,
    WebhookPayload,
)

# Convenience alias
get_provider = get_identity_verification_provider

__all__ = [
    'get_provider',
    'get_identity_verification_provider',
    'IdentityVerificationProviderAdapter',
    'VerificationSessionCreate',
    'WebhookPayload',
    'IdentityVerificationMixin',
    'KYCStatusMixin',
    'AbstractIdentityVerificationSession',
]
