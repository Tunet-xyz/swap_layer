"""
Payment provider implementations.

Lazy imports to avoid loading provider dependencies unless actually used.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .paypal import PayPalPaymentProvider
    from .square import SquarePaymentProvider
    from .stripe import StripePaymentProvider

__all__ = [
    "PayPalPaymentProvider",
    "SquarePaymentProvider",
    "StripePaymentProvider",
]


def __getattr__(name: str):
    """Lazy import providers only when accessed."""
    if name == "StripePaymentProvider":
        from .stripe import StripePaymentProvider

        return StripePaymentProvider
    if name == "PayPalPaymentProvider":
        from .paypal import PayPalPaymentProvider

        return PayPalPaymentProvider
    if name == "SquarePaymentProvider":
        from .square import SquarePaymentProvider

        return SquarePaymentProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")