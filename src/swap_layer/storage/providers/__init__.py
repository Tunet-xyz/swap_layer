"""
Storage providers initialization.
"""

from .django_storage import DjangoStorageAdapter
from .local import LocalFileStorageProvider

__all__ = [
    "LocalFileStorageProvider",
    "DjangoStorageAdapter",
]
