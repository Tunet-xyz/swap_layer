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
        - 'gcs': Google Cloud Storage (direct GCS SDK)
          Configure: bucket_name, credentials_path, project_id, location
        - 'django': Uses django-storages (supports S3, Azure, GCS, etc.)
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
        elif provider == "gcs":
            from .providers.gcs import GCSStorageProvider

            return GCSStorageProvider(
                bucket_name=getattr(settings.storage, 'bucket_name', ''),
                credentials_path=getattr(settings.storage, 'credentials_path', None),
                project_id=getattr(settings.storage, 'project_id', None),
                location=getattr(settings.storage, 'location', 'europe-west1'),
                storage_class=getattr(settings.storage, 'storage_class', 'STANDARD'),
            )
        elif provider == "django":
            from .providers.django_storage import DjangoStorageAdapter

            return DjangoStorageAdapter()
    else:
        # Fallback to legacy Django settings for backward compatibility
        from django.conf import settings as django_settings

        provider = getattr(django_settings, "STORAGE_PROVIDER", "local").lower()

    if provider == "gcs":
        from django.conf import settings as django_settings

        from .providers.gcs import GCSStorageProvider

        return GCSStorageProvider(
            bucket_name=getattr(django_settings, 'GCS_BUCKET_NAME', ''),
            credentials_path=getattr(django_settings, 'GCS_CREDENTIALS_PATH', None),
            project_id=getattr(django_settings, 'GCS_PROJECT_ID', None),
            location=getattr(django_settings, 'GCS_LOCATION', 'europe-west1'),
            storage_class=getattr(django_settings, 'GCS_STORAGE_CLASS', 'STANDARD'),
        )
    elif provider == "django":
        from .providers.django_storage import DjangoStorageAdapter

        return DjangoStorageAdapter()
    elif provider == "local":
        from .providers.local import LocalFileStorageProvider

        return LocalFileStorageProvider()
    else:
        raise ValueError(
            f"Unsupported storage provider: '{provider}'. "
            f"Supported: 'local', 'gcs', 'django'. "
            f"For S3/Azure, use STORAGE_PROVIDER='django' with django-storages."
        )
