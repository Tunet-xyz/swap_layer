"""
Factory function for creating SMS provider instances.
"""
from swap_layer.config import settings
from .adapter import SMSProviderAdapter
from .providers.twilio_sms import TwilioSMSProvider


def get_sms_provider() -> SMSProviderAdapter:
    """
    Get the configured SMS provider instance.
    
    The provider is determined by the SMS_PROVIDER setting.
    Defaults to 'twilio' if not specified.
    
    Returns:
        SMSProviderAdapter: Instance of the configured provider
    
    Raises:
        ValueError: If an unsupported provider is specified
    """
    provider = getattr(settings, 'SMS_PROVIDER', 'twilio').lower()
    
    if provider == 'twilio':
        return TwilioSMSProvider()
    elif provider == 'sns':
        from .providers.sns import SNSSMSProvider
        return SNSSMSProvider()
    else:
        raise ValueError(f"Unsupported SMS provider: {provider}")
