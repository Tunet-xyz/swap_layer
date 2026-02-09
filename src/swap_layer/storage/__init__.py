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
from .security import (
    ScopedStorageProvider,
    StoragePermission,
    StorageSecurityContext,
    storage_context,
    validate_storage_context,
)

# Convenience alias
get_provider = get_storage_provider

__all__ = [
    # Factory
    "get_provider",
    "get_storage_provider",
    # Abstract adapter
    "StorageProviderAdapter",
    # Security context (mirrors database RLS)
    "StorageSecurityContext",
    "StoragePermission",
    "ScopedStorageProvider",
    "storage_context",
    "validate_storage_context",
    # Exceptions
    "StorageError",
    "StorageUploadError",
    "StorageDownloadError",
    "StorageFileNotFoundError",
    "StorageDeleteError",
    "StorageCopyError",
    "StorageMoveError",
]
