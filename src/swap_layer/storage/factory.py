"""
Factory function for creating storage provider instances.
"""

from django.conf import settings

from .adapter import StorageProviderAdapter
from .providers.local import LocalFileStorageProvider


def get_storage_provider() -> StorageProviderAdapter:
    """
    Get the configured storage provider instance.

    The provider is determined by the STORAGE_PROVIDER Django setting.
    Defaults to 'local' if not specified.

    Returns:
        StorageProviderAdapter: Instance of the configured provider

    Raises:
        ValueError: If an unsupported provider is specified

    Supported Providers:
        - 'local': Local file system storage (development)
        - 'django': Uses django-storages (RECOMMENDED for production)
          Supports: S3, Azure, GCS, Dropbox, FTP, SFTP, etc.
          Configure via DEFAULT_FILE_STORAGE in settings.py
    """
    provider = getattr(settings, "STORAGE_PROVIDER", "local").lower()

    if provider == "django":
        from .providers.django_storage import DjangoStorageAdapter

        return DjangoStorageAdapter()
    elif provider == "local":
        return LocalFileStorageProvider()
    else:
        raise ValueError(
            f"Unsupported storage provider: '{provider}'. "
            f"Supported: 'local', 'django' (recommended). "
            f"For S3/Azure/GCS, use STORAGE_PROVIDER='django' with django-storages."
        )
