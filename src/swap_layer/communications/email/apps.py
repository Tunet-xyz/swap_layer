from django.apps import AppConfig


class EmailConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "swap_layer.email"
    verbose_name = "Email Infrastructure"
