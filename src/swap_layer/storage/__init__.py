"""
Storage abstraction layer for file storage operations.
"""

from .adapter import (
    StorageCopyError,
    StorageDeleteError,
    StorageDownloadError,
    StorageError,
    StorageFileNotFoundError,
    StorageMoveError,
    StorageProviderAdapter,
    StorageUploadError,
)
from .factory import get_storage_provider

# Convenience alias
get_provider = get_storage_provider

__all__ = [
    "get_provider",
    "get_storage_provider",
    "StorageProviderAdapter",
    "StorageError",
    "StorageUploadError",
    "StorageDownloadError",
    "StorageFileNotFoundError",
    "StorageDeleteError",
    "StorageCopyError",
    "StorageMoveError",
]
