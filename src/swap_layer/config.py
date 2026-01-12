"""
Django settings wrapper for SwapLayer.

SwapLayer is Django-only and reads all configuration from Django settings.
This module provides a simple proxy to django.conf.settings for convenience.
"""

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured


def get_setting(key: str, default=None):
    """
    Get a setting from Django settings.

    Args:
        key: Setting name (e.g., 'EMAIL_PROVIDER')
        default: Default value if setting not found

    Returns:
        Setting value from Django settings or default

    Raises:
        ImproperlyConfigured: If Django settings are not configured
    """
    if not django_settings.configured:
        raise ImproperlyConfigured(
            "Django settings must be configured before using SwapLayer. "
            "Ensure your Django project is properly initialized."
        )

    return getattr(django_settings, key, default)


# Re-export django settings for direct access
settings = django_settings
