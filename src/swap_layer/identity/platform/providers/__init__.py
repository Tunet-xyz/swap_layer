"""
Identity Platform provider implementations.

Lazy imports to avoid loading provider dependencies unless actually used.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .auth0.client import Auth0Client
    from .workos.client import WorkOSClient

__all__ = [
    "Auth0Client",
    "WorkOSClient",
]


def __getattr__(name: str):
    """Lazy import providers only when accessed."""
    if name == "Auth0Client":
        from .auth0.client import Auth0Client
        return Auth0Client
    elif name == "WorkOSClient":
        from .workos.client import WorkOSClient
        return WorkOSClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
