"""
Payment provider implementations.

Lazy imports to avoid loading provider dependencies unless actually used.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .stripe import StripePaymentProvider

__all__ = [
    "StripePaymentProvider",
]


def __getattr__(name: str):
    """Lazy import providers only when accessed."""
    if name == "StripePaymentProvider":
        from .stripe import StripePaymentProvider
        return StripePaymentProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
