from swap_layer.settings import get_swaplayer_settings

from .adapter import IdentityVerificationProviderAdapter


def get_identity_verification_provider() -> IdentityVerificationProviderAdapter:
    """
    Factory function to return the configured Identity Verification Provider.
    This allows switching vendors by changing the provider in SwapLayerSettings.

    Returns:
        IdentityVerificationProviderAdapter: The configured provider instance

    Raises:
        ValueError: If the provider is not supported or not configured
    """
    # Get provider from SwapLayerSettings
    settings = get_swaplayer_settings()

    if settings.verification:
        provider = settings.verification.provider
    else:
        # Fallback to legacy Django settings for backward compatibility
        from django.conf import settings as django_settings

        provider = getattr(django_settings, "IDENTITY_VERIFICATION_PROVIDER", "stripe")

    if provider == "stripe":
        from .providers.stripe import StripeIdentityVerificationProvider

        return StripeIdentityVerificationProvider()
    # Add other providers here as they are implemented
    # elif provider == 'onfido':
    #     from .providers.onfido import OnfidoIdentityVerificationProvider
    #     return OnfidoIdentityVerificationProvider()
    else:
        raise ValueError(f"Unknown Identity Verification Provider: {provider}")
