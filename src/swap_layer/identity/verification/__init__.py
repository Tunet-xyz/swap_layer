"""
Identity verification infrastructure module.
Provides an abstraction layer for identity verification providers (Stripe, Onfido, etc.).

Note: Django models must be imported directly when needed to avoid Django
configuration requirements:
    from swap_layer.identity.verification.models import IdentityVerificationMixin
"""

from .adapter import IdentityVerificationProviderAdapter
from .factory import get_identity_verification_provider

# DO NOT import models at module level - they require Django to be configured
# from .models import (
#     AbstractIdentityVerificationSession,
#     IdentityVerificationMixin,
#     KYCStatusMixin,
#     VerificationSessionCreate,
#     WebhookPayload,
# )

# Convenience alias
get_provider = get_identity_verification_provider

__all__ = [
    "get_provider",
    "get_identity_verification_provider",
    "IdentityVerificationProviderAdapter",
    # Models available via: from swap_layer.identity.verification.models import ...
    # 'VerificationSessionCreate',
    # 'WebhookPayload',
    # 'IdentityVerificationMixin',
    # 'KYCStatusMixin',
    # 'AbstractIdentityVerificationSession',
]
