"""
Factory function for creating SMS provider instances.
"""
from swap_layer.settings import get_swaplayer_settings

from .adapter import SMSProviderAdapter
from .providers.twilio_sms import TwilioSMSProvider


def get_sms_provider() -> SMSProviderAdapter:
    """
    Get the configured SMS provider instance.

    The provider is determined by SwapLayerSettings configuration.
    Defaults to 'twilio' if not specified.

    Returns:
        SMSProviderAdapter: Instance of the configured provider

    Raises:
        ValueError: If an unsupported provider is specified
    """
    # Get provider from SwapLayerSettings
    settings = get_swaplayer_settings()

    if settings.communications and settings.communications.sms:
        provider = settings.communications.sms.provider.lower()
    else:
        # Fallback to legacy Django settings for backward compatibility
        from django.conf import settings as django_settings
        provider = getattr(django_settings, 'SMS_PROVIDER', 'twilio').lower()

    if provider == 'twilio':
        return TwilioSMSProvider()
    elif provider == 'sns':
        from .providers.sns import SNSSMSProvider
        return SNSSMSProvider()
    else:
        raise ValueError(f"Unsupported SMS provider: {provider}")
