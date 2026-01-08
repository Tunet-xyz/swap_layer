"""
SMS abstraction layer for sending text messages.
"""

from .adapter import (
    SMSError,
    SMSInvalidPhoneNumberError,
    SMSMessageNotFoundError,
    SMSProviderAdapter,
    SMSSendError,
)
from .factory import get_sms_provider

# Convenience alias
get_provider = get_sms_provider

__all__ = [
    "get_provider",
    "get_sms_provider",
    "SMSProviderAdapter",
    "SMSError",
    "SMSSendError",
    "SMSMessageNotFoundError",
    "SMSInvalidPhoneNumberError",
]
