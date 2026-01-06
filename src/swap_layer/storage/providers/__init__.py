"""
Storage providers initialization.
"""
from .local import LocalFileStorageProvider
from .django_storage import DjangoStorageAdapter

__all__ = [
    'LocalFileStorageProvider',
    'DjangoStorageAdapter',
]
