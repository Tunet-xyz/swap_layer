"""
Factory function for creating SMS provider instances.
"""

from swap_layer.settings import get_swaplayer_settings

from .adapter import SMSProviderAdapter


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
        sms_config = settings.communications.sms
        provider = sms_config.provider.lower()

        # Pass Twilio config from SwapLayerSettings if available
        if provider == "twilio" and sms_config.twilio:
            from .providers.twilio_sms import TwilioSMSProvider

            return TwilioSMSProvider(
                account_sid=sms_config.twilio.account_sid,
                auth_token=sms_config.twilio.auth_token,
                from_number=sms_config.twilio.from_number,
            )
    else:
        # Fallback to legacy Django settings for backward compatibility
        from django.conf import settings as django_settings

        provider = getattr(django_settings, "SMS_PROVIDER", "twilio").lower()

    if provider == "twilio":
        from .providers.twilio_sms import TwilioSMSProvider

        return TwilioSMSProvider()
    elif provider == "sns":
        from .providers.sns import SNSSMSProvider

        return SNSSMSProvider()
    else:
        raise ValueError(f"Unsupported SMS provider: {provider}")
