import warnings

from django.apps import AppConfig


class IdentityVerificationAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "swap_layer.identity.verification"
    label = "swap_layer_identity_verification"
    verbose_name = "Identity Verification"


def __getattr__(name: str) -> type[AppConfig]:
    # The former class name stays importable through 1.x (not as a module
    # attribute, so Django's AppConfig discovery still finds one class).
    if name == "IdentityConfig":
        warnings.warn(
            "swap_layer.identity.verification.apps.IdentityConfig is now IdentityVerificationAppConfig",
            DeprecationWarning,
            stacklevel=2,
        )
        return IdentityVerificationAppConfig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
