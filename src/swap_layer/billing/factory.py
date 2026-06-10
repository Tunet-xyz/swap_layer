from swap_layer.settings import get_swaplayer_settings

from .adapter import PaymentProviderAdapter


def get_payment_provider() -> PaymentProviderAdapter:
    """
    Factory function to return the configured Payment Provider.
    This allows switching vendors by changing the provider in SwapLayerSettings.

    Returns:
        PaymentProviderAdapter: The configured payment provider instance

    Raises:
        ValueError: If the provider is not supported or not configured
    """
    settings = get_swaplayer_settings()

    if settings.billing:
        provider = settings.billing.provider
        if provider == "stripe" and settings.billing.stripe:
            from .providers.stripe import StripePaymentProvider

            return StripePaymentProvider(
                secret_key=settings.billing.stripe.secret_key,
                publishable_key=settings.billing.stripe.publishable_key,
                webhook_secret=settings.billing.stripe.webhook_secret,
            )
        if provider == "paypal" and settings.billing.paypal:
            from .providers.paypal import PayPalPaymentProvider

            return PayPalPaymentProvider(
                client_id=settings.billing.paypal.client_id,
                client_secret=settings.billing.paypal.client_secret,
                webhook_id=settings.billing.paypal.webhook_id,
                sandbox=settings.billing.paypal.sandbox,
            )
    else:
        # Fallback to legacy Django settings for backward compatibility
        from django.conf import settings as django_settings

        provider = getattr(django_settings, "PAYMENT_PROVIDER", "stripe")

        if provider == "paypal":
            from .providers.paypal import PayPalPaymentProvider

            sandbox = getattr(django_settings, "PAYPAL_SANDBOX", True)
            if isinstance(sandbox, str):
                sandbox = sandbox.lower() not in {"0", "false", "no", "off"}
            return PayPalPaymentProvider(
                client_id=getattr(django_settings, "PAYPAL_CLIENT_ID", None),
                client_secret=getattr(django_settings, "PAYPAL_CLIENT_SECRET", None)
                or getattr(django_settings, "PAYPAL_SECRET", None),
                webhook_id=getattr(django_settings, "PAYPAL_WEBHOOK_ID", None),
                sandbox=sandbox,
            )

    if provider == "stripe":
        from .providers.stripe import StripePaymentProvider

        return StripePaymentProvider()

    raise ValueError(f"Unknown Payment Provider: {provider}")