"""
Storage abstraction layer for file storage operations.
"""

from .factory import get_storage_provider
from .adapter import (
    StorageProviderAdapter,
    StorageError,
    StorageUploadError,
    StorageDownloadError,
    StorageFileNotFoundError,
    StorageDeleteError,
    StorageCopyError,
    StorageMoveError,
)

# Convenience alias
get_provider = get_storage_provider

__all__ = [
    'get_provider',
    'get_storage_provider',
    'StorageProviderAdapter',
    'StorageError',
    'StorageUploadError',
    'StorageDownloadError',
    'StorageFileNotFoundError',
    'StorageDeleteError',
    'StorageCopyError',
    'StorageMoveError',
]
