"""
SwapLayer - Swap Providers with Zero Vendor Lock-in. For Django SaaS.
"""

from typing import Any

from .billing.factory import get_payment_provider
from .communications.email.factory import get_email_provider
from .communications.sms.factory import get_sms_provider

# Export exceptions for error handling
from .exceptions import (
    ConfigurationError,
    EnvironmentVariableError,
    ModuleNotConfiguredError,
    MultiTenantConfigError,
    ProviderConfigMismatchError,
    ProviderError,
    StripeKeyError,
    SwapLayerError,
    TwilioConfigError,
    ValidationError,
    WorkOSConfigError,
)
from .identity.platform.factory import get_identity_client
from .identity.verification.factory import get_identity_verification_provider

# Export settings management
from .settings import (
    SwapLayerSettings,
    get_swaplayer_settings,
    validate_swaplayer_config,
)
from .storage.factory import get_storage_provider

__version__ = "0.2.3"


def get_provider(service_type: str, **kwargs) -> Any:
    """
    Unified entry point for getting a provider.

    This is the single import you need for all SwapLayer services:

        from swap_layer import get_provider

        # Get any provider by service type
        email = get_provider('email')
        billing = get_provider('billing')
        storage = get_provider('storage')
        sms = get_provider('sms')
        identity = get_provider('identity')

    Args:
        service_type: Service type - 'email', 'billing', 'storage', 'sms',
                      'identity', or 'verification'
        **kwargs: Additional arguments (e.g., app_name for identity)

    Returns:
        The configured provider adapter instance

    Raises:
        ValueError: If service_type is not recognized
    """
    service = service_type.lower()

    if service == "email":
        return get_email_provider()
    elif service in ("billing", "payment", "payments"):
        return get_payment_provider()
    elif service == "storage":
        return get_storage_provider()
    elif service == "sms":
        return get_sms_provider()
    elif service in ("identity", "auth", "oauth"):
        return get_identity_client(**kwargs)
    elif service in ("verification", "kyc"):
        return get_identity_verification_provider()
    else:
        raise ValueError(
            f"Unknown service type: '{service_type}'. "
            f"Valid options: email, billing, storage, sms, identity, verification"
        )


__all__ = [
    "get_provider",
    "get_email_provider",
    "get_payment_provider",
    "get_storage_provider",
    "get_sms_provider",
    "get_identity_client",
    "get_identity_verification_provider",
    # Settings management
    "SwapLayerSettings",
    "get_swaplayer_settings",
    "validate_swaplayer_config",
    # Exceptions
    "SwapLayerError",
    "ConfigurationError",
    "ValidationError",
    "ProviderError",
    "StripeKeyError",
    "TwilioConfigError",
    "WorkOSConfigError",
    "ProviderConfigMismatchError",
    "ModuleNotConfiguredError",
    "EnvironmentVariableError",
    "MultiTenantConfigError",
]
