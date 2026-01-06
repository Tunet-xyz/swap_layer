"""
SwapLayer - Swap Providers with Zero Vendor Lock-in. For Django SaaS.
"""
from typing import Any

from .email.factory import get_email_provider
from .payments.factory import get_payment_provider
from .storage.factory import get_storage_provider
from .sms.factory import get_sms_provider
from .identity.platform.factory import get_identity_client
from .identity.verification.factory import get_identity_verification_provider

# Export settings management
from .settings import (
    SwapLayerSettings,
    get_swaplayer_settings,
    validate_swaplayer_config,
)

# Export exceptions for error handling
from .exceptions import (
    SwapLayerError,
    ConfigurationError,
    ValidationError,
    ProviderError,
    StripeKeyError,
    TwilioConfigError,
    WorkOSConfigError,
    ProviderConfigMismatchError,
    ModuleNotConfiguredError,
    EnvironmentVariableError,
    MultiTenantConfigError,
)

__version__ = "0.1.0"

def get_provider(service_type: str, **kwargs) -> Any:
    """
    Unified entry point for getting a provider.
    
    This is the single import you need for all SwapLayer services:
    
        from swap_layer import get_provider
        
        # Get any provider by service type
        email = get_provider('email')
        payments = get_provider('payments')
        storage = get_provider('storage')
        sms = get_provider('sms')
        identity = get_provider('identity')
    
    Args:
        service_type: Service type - 'email', 'payments', 'storage', 'sms', 
                      'identity', or 'verification'
        **kwargs: Additional arguments (e.g., app_name for identity)
    
    Returns:
        The configured provider adapter instance
        
    Raises:
        ValueError: If service_type is not recognized
    """
    service = service_type.lower()
    
    if service == 'email':
        return get_email_provider()
    elif service in ('payment', 'payments'):
        return get_payment_provider()
    elif service == 'storage':
        return get_storage_provider()
    elif service == 'sms':
        return get_sms_provider()
    elif service in ('identity', 'auth', 'oauth'):
        return get_identity_client(**kwargs)
    elif service in ('verification', 'kyc'):
        return get_identity_verification_provider()
    else:
        raise ValueError(
            f"Unknown service type: '{service_type}'. "
            f"Valid options: email, payments, storage, sms, identity, verification"
        )

__all__ = [
    'get_provider',
    'get_email_provider',
    'get_payment_provider',
    'get_storage_provider',
    'get_sms_provider',
    'get_identity_client',
    'get_identity_verification_provider',
    # Settings management
    'SwapLayerSettings',
    'get_swaplayer_settings',
    'validate_swaplayer_config',
    # Exceptions
    'SwapLayerError',
    'ConfigurationError',
    'ValidationError',
    'ProviderError',
    'StripeKeyError',
    'TwilioConfigError',
    'WorkOSConfigError',
    'ProviderConfigMismatchError',
    'ModuleNotConfiguredError',
    'EnvironmentVariableError',
    'MultiTenantConfigError',
]
