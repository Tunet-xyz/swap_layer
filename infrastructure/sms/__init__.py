"""
SMS abstraction layer for sending text messages.
"""
from .adapter import (
    SMSProviderAdapter,
    SMSError,
    SMSSendError,
    SMSMessageNotFoundError,
    SMSInvalidPhoneNumberError,
)

__all__ = [
    'SMSProviderAdapter',
    'SMSError',
    'SMSSendError',
    'SMSMessageNotFoundError',
    'SMSInvalidPhoneNumberError',
]
