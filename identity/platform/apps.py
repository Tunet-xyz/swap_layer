from django.apps import AppConfig

class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'identity.platform'
    label = 'identity_platform'
    verbose_name = 'Identity Platform'
