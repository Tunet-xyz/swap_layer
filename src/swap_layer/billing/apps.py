from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "swap_layer.billing"
    label = "billing"
    verbose_name = "Billing Infrastructure"
