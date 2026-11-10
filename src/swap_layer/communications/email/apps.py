import warnings

from django.apps import AppConfig


class EmailAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "swap_layer.communications.email"
    label = "swap_layer_email"
    verbose_name = "Email Infrastructure"


def __getattr__(name: str) -> type[AppConfig]:
    # The former class name stays importable through 1.x (not as a module
    # attribute, so Django's AppConfig discovery still finds one class).
    if name == "EmailConfig":
        warnings.warn(
            "swap_layer.communications.email.apps.EmailConfig is now EmailAppConfig",
            DeprecationWarning,
            stacklevel=2,
        )
        return EmailAppConfig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
