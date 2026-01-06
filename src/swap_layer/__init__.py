"""
SwapLayer - The Anti-Vendor-Lock-in Framework.
"""
from typing import Any

from .email.factory import get_email_provider
from .payments.factory import get_payment_provider
from .storage.factory import get_storage_provider
from .sms.factory import get_sms_provider
from .identity.platform.factory import get_identity_client as get_identity_provider

__version__ = "0.1.0"

def get_provider(service_type: str, **kwargs) -> Any:
    """
    Unified entry point for getting a provider.
    
    Args:
        service_type (str): The type of service ('email', 'payment', 'storage', 'sms', 'identity').
        **kwargs: Additional arguments to pass to the factory (e.g. app_name for identity).
    
    Returns:
        The requested provider adapter.
    """
    service = service_type.lower()
    
    if service == 'email':
        return get_email_provider()
    elif service == 'payment' or service == 'payments':
        return get_payment_provider()
    elif service == 'storage':
        return get_storage_provider()
    elif service == 'sms':
        return get_sms_provider()
    elif service == 'identity' or service == 'auth':
        return get_identity_provider(**kwargs)
    else:
        raise ValueError(f"Unknown service type: {service_type}")
