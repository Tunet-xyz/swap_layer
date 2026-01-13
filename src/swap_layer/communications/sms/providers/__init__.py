"""
SMS providers initialization.

Lazy imports to avoid loading provider dependencies unless actually used.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .sns import SNSSMSProvider
    from .twilio_sms import TwilioSMSProvider

__all__ = [
    "TwilioSMSProvider",
    "SNSSMSProvider",
]


def __getattr__(name: str):
    """Lazy import providers only when accessed."""
    if name == "TwilioSMSProvider":
        from .twilio_sms import TwilioSMSProvider
        return TwilioSMSProvider
    elif name == "SNSSMSProvider":
        from .sns import SNSSMSProvider
        return SNSSMSProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
