"""
SMS abstraction layer for sending text messages.
"""

from .factory import get_sms_provider
from .adapter import (
    SMSProviderAdapter,
    SMSError,
    SMSSendError,
    SMSMessageNotFoundError,
    SMSInvalidPhoneNumberError,
)

# Convenience alias
get_provider = get_sms_provider

__all__ = [
    'get_provider',
    'get_sms_provider',
    'SMSProviderAdapter',
    'SMSError',
    'SMSSendError',
    'SMSMessageNotFoundError',
    'SMSInvalidPhoneNumberError',
]
