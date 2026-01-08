"""
Communications module - Email and SMS unified.
"""

from .email.factory import get_email_provider
from .sms.factory import get_sms_provider

__all__ = ["get_email_provider", "get_sms_provider"]
