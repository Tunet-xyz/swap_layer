import warnings

from django.apps import AppConfig


class BillingAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "swap_layer.billing"
    label = "swap_layer_billing"
    verbose_name = "Billing Infrastructure"


def __getattr__(name: str) -> type[AppConfig]:
    # The former class name stays importable through 1.x (not as a module
    # attribute, so Django's AppConfig discovery still finds one class).
    if name == "BillingConfig":
        warnings.warn(
            "swap_layer.billing.apps.BillingConfig is now BillingAppConfig",
            DeprecationWarning,
            stacklevel=2,
        )
        return BillingAppConfig
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
