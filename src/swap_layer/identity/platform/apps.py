import warnings

from django.apps import AppConfig


class IdentityPlatformAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "swap_layer.identity.platform"
    label = "swap_layer_identity_platform"
    verbose_name = "Identity Platform"


def __getattr__(name: str) -> type[AppConfig]:
    # The former class name stays importable through 1.x (not as a module
    # attribute, so Django's AppConfig discovery still finds one class).
    if name == "AuthenticationConfig":
        warnings.warn(
            "swap_layer.identity.platform.apps.AuthenticationConfig is now IdentityPlatformAppConfig",
            DeprecationWarning,
            stacklevel=2,
        )
        return IdentityPlatformAppConfig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
