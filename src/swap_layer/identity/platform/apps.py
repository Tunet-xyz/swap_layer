from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "swap_layer.identity.platform"
    label = "identity_platform"
    verbose_name = "Identity Platform"
