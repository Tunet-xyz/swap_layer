import warnings

from django.apps import AppConfig


class SMSAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "swap_layer.communications.sms"
    label = "swap_layer_sms"
    verbose_name = "SMS Infrastructure"


def __getattr__(name: str) -> type[AppConfig]:
    # The former class name stays importable through 1.x (not as a module
    # attribute, so Django's AppConfig discovery still finds one class).
    if name == "SmsConfig":
        warnings.warn(
            "swap_layer.communications.sms.apps.SmsConfig is now SMSAppConfig",
            DeprecationWarning,
            stacklevel=2,
        )
        return SMSAppConfig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
