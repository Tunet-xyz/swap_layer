"""Optional access to legacy Django configuration from otherwise standalone providers."""

from typing import Any


def legacy_setting(name: str, default: Any = None) -> Any:
    try:
        from django.conf import settings
    except ImportError:
        return default
    if not settings.configured:
        return default
    return getattr(settings, name, default)
