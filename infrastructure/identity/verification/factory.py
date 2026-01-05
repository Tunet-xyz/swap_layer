from django.conf import settings
from .adapter import IdentityVerificationProviderAdapter


def get_identity_verification_provider() -> IdentityVerificationProviderAdapter:
    """
    Factory function to return the configured Identity Verification Provider.
    This allows switching vendors by changing the IDENTITY_VERIFICATION_PROVIDER setting.
    
    Returns:
        IdentityVerificationProviderAdapter: The configured provider instance
        
    Raises:
        ValueError: If the provider is not supported or not configured
    """
    provider = getattr(settings, 'IDENTITY_VERIFICATION_PROVIDER', 'stripe')
    
    if provider == 'stripe':
        from .providers.stripe import StripeIdentityVerificationProvider
        return StripeIdentityVerificationProvider()
    # Add other providers here as they are implemented
    # elif provider == 'onfido':
    #     from .providers.onfido import OnfidoIdentityVerificationProvider
    #     return OnfidoIdentityVerificationProvider()
    else:
        raise ValueError(f"Unknown Identity Verification Provider: {provider}")
