"""
Identity configuration lookup.

``SWAPLAYER.identity`` (or ``configure(identity=...)``) is read first. The
legacy Django settings ``IDENTITY_PROVIDER``, ``WORKOS_APPS``, ``AUTH0_APPS``
and ``AUTH0_DEVELOPER_DOMAIN`` remain a fallback, validated by the same models.
"""

from typing import Any

from swap_layer.settings import (
    Auth0AppConfig,
    IdentityPlatformConfig,
    WorkOSAppConfig,
    get_swaplayer_settings,
    legacy_app_config,
)


def _django_setting(name: str, default: Any = None) -> Any:
    try:
        from django.conf import settings
    except ImportError:
        return default
    if not settings.configured:
        return default
    return getattr(settings, name, default)


def _identity() -> IdentityPlatformConfig | None:
    return get_swaplayer_settings().identity


def identity_provider() -> str:
    """Return the configured identity provider name (default ``workos``)."""
    identity = _identity()
    if identity is not None:
        return identity.provider
    return str(_django_setting("IDENTITY_PROVIDER", "workos"))


def workos_app_config(app_name: str) -> WorkOSAppConfig:
    """Return a validated WorkOS app configuration."""
    identity = _identity()
    if identity is not None and identity.workos_apps and app_name in identity.workos_apps:
        return identity.workos_apps[app_name]
    raw = (_django_setting("WORKOS_APPS") or {}).get(app_name)
    if not raw:
        raise ValueError(
            f"WorkOS configuration for '{app_name}' not found in "
            "SWAPLAYER.identity.workos_apps or settings.WORKOS_APPS"
        )
    return WorkOSAppConfig.model_validate(legacy_app_config(WorkOSAppConfig, raw))


def auth0_app_config(app_name: str) -> tuple[Auth0AppConfig, str]:
    """Return a validated Auth0 app configuration and the Auth0 domain."""
    identity = _identity()
    if identity is not None and identity.auth0_apps and app_name in identity.auth0_apps:
        app = identity.auth0_apps[app_name]
        domain = identity.auth0_domain or _django_setting("AUTH0_DEVELOPER_DOMAIN", "")
    else:
        raw = (_django_setting("AUTH0_APPS") or {}).get(app_name)
        if not raw:
            raise ValueError(
                f"Auth0 configuration for '{app_name}' not found in "
                "SWAPLAYER.identity.auth0_apps or settings.AUTH0_APPS"
            )
        app = Auth0AppConfig.model_validate(legacy_app_config(Auth0AppConfig, raw))
        domain = _django_setting("AUTH0_DEVELOPER_DOMAIN", "")
    if not domain:
        raise ValueError(
            "Auth0 needs a domain: set SWAPLAYER.identity.auth0_domain "
            "or settings.AUTH0_DEVELOPER_DOMAIN"
        )
    return app, str(domain)
