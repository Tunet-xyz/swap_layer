"""
Factory function for creating storage provider instances.
"""

from swap_layer.settings import get_swaplayer_settings

from .adapter import StorageProviderAdapter


def get_storage_provider() -> StorageProviderAdapter:
    """
    Get the configured storage provider instance.

    The provider is determined by SwapLayerSettings configuration.
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
    # Get provider from SwapLayerSettings
    settings = get_swaplayer_settings()

    if settings.storage:
        provider = settings.storage.provider.lower()
        # Pass storage config from SwapLayerSettings if available
        if provider == "local":
            from .providers.local import LocalFileStorageProvider

            return LocalFileStorageProvider(
                base_path=settings.storage.media_root, base_url=settings.storage.media_url
            )
        elif provider == "django":
            from .providers.django_storage import DjangoStorageAdapter

            return DjangoStorageAdapter()
    else:
        # Fallback to legacy Django settings for backward compatibility
        from django.conf import settings as django_settings

        provider = getattr(django_settings, "STORAGE_PROVIDER", "local").lower()

    if provider == "django":
        from .providers.django_storage import DjangoStorageAdapter

        return DjangoStorageAdapter()
    elif provider == "local":
        from .providers.local import LocalFileStorageProvider

        return LocalFileStorageProvider()
    else:
        raise ValueError(
            f"Unsupported storage provider: '{provider}'. "
            f"Supported: 'local', 'django' (recommended). "
            f"For S3/Azure/GCS, use STORAGE_PROVIDER='django' with django-storages."
        )
