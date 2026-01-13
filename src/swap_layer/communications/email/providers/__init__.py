"""
Email Provider Implementations

This package contains concrete implementations of the EmailProviderAdapter
for different email service providers.

Lazy imports to avoid loading provider dependencies unless actually used.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .django_email import DjangoEmailAdapter
    from .smtp import SMTPEmailProvider

__all__ = [
    "SMTPEmailProvider",
    "DjangoEmailAdapter",
]


def __getattr__(name: str):
    """Lazy import providers only when accessed."""
    if name == "SMTPEmailProvider":
        from .smtp import SMTPEmailProvider
        return SMTPEmailProvider
    elif name == "DjangoEmailAdapter":
        from .django_email import DjangoEmailAdapter
        return DjangoEmailAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
