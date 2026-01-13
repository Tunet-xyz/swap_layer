"""
Identity verification provider implementations.

Lazy imports to avoid loading provider dependencies unless actually used.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .stripe import StripeIdentityVerificationProvider

__all__ = [
    "StripeIdentityVerificationProvider",
]


def __getattr__(name: str):
    """Lazy import providers only when accessed."""
    if name == "StripeIdentityVerificationProvider":
        from .stripe import StripeIdentityVerificationProvider
        return StripeIdentityVerificationProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
