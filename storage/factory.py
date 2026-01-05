"""
Factory function for creating storage provider instances.
"""
from swap_layer.config import settings
from .adapter import StorageProviderAdapter
from .providers.local import LocalFileStorageProvider


def get_storage_provider() -> StorageProviderAdapter:
    """
    Get the configured storage provider instance.
    
    The provider is determined by the STORAGE_PROVIDER setting.
    Defaults to 'local' if not specified.
    
    Returns:
        StorageProviderAdapter: Instance of the configured provider
    
    Raises:
        ValueError: If an unsupported provider is specified
    """
    provider = getattr(settings, 'STORAGE_PROVIDER', 'local').lower()
    
    if provider == 'django':
        from .providers.django_storage import DjangoStorageAdapter
        return DjangoStorageAdapter()
    elif provider == 'local':
        return LocalFileStorageProvider()
    elif provider == 's3':
        # Deprecated: Use 'django' provider with django-storages configured for S3
        from .providers.s3 import S3StorageProvider
        return S3StorageProvider()
    elif provider == 'azure':
        # Deprecated: Use 'django' provider with django-storages configured for Azure
        from .providers.azure import AzureBlobStorageProvider
        return AzureBlobStorageProvider()
    else:
        raise ValueError(f"Unsupported storage provider: {provider}")
