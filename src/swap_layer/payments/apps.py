from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'swap_layer.payments'
    label = 'payments'
    verbose_name = 'Payments Infrastructure'
