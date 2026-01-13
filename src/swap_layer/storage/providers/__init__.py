"""
Storage providers initialization.

Lazy imports to avoid loading provider dependencies unless actually used.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .django_storage import DjangoStorageAdapter
    from .local import LocalFileStorageProvider

__all__ = [
    "LocalFileStorageProvider",
    "DjangoStorageAdapter",
]


def __getattr__(name: str):
    """Lazy import providers only when accessed."""
    if name == "LocalFileStorageProvider":
        from .local import LocalFileStorageProvider
        return LocalFileStorageProvider
    elif name == "DjangoStorageAdapter":
        from .django_storage import DjangoStorageAdapter
        return DjangoStorageAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
