from swap_layer.settings import get_swaplayer_settings

from .adapter import PaymentProviderAdapter

BILLING_PROVIDERS = ("stripe", "paypal", "square")


def get_payment_provider(provider: str | None = None) -> PaymentProviderAdapter:
    """
    Factory function to return the configured Payment Provider.
    This allows switching vendors by changing the provider in SwapLayerSettings.

    Args:
        provider: Build this provider ("stripe", "paypal" or "square") instead of the
            configured ``billing.provider``: from its own block in the billing settings,
            or else from its legacy Django settings. Migrations use it to reach the
            target provider.

    Returns:
        PaymentProviderAdapter: The configured payment provider instance

    Raises:
        ValueError: If the provider is not supported or not configured
    """
    if provider is not None and provider not in BILLING_PROVIDERS:
        raise ValueError(f"Unknown Payment Provider: {provider}")
    settings = get_swaplayer_settings()

    if settings.billing and (provider is None or getattr(settings.billing, provider) is not None):
        provider = provider or settings.billing.provider
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
        if provider == "square" and settings.billing.square:
            from .providers.square import SquarePaymentProvider

            return SquarePaymentProvider(
                access_token=settings.billing.square.access_token,
                location_id=settings.billing.square.location_id,
                webhook_signature_key=settings.billing.square.webhook_signature_key,
                webhook_notification_url=settings.billing.square.webhook_notification_url,
                sandbox=settings.billing.square.sandbox,
                api_version=settings.billing.square.api_version,
            )
    else:
        # Fallback to legacy Django settings for backward compatibility
        from django.conf import settings as django_settings

        provider = provider or getattr(django_settings, "PAYMENT_PROVIDER", "stripe")

        if provider == "paypal":
            from .providers.paypal import PayPalPaymentProvider

            sandbox = getattr(django_settings, "PAYPAL_SANDBOX", True)
            if isinstance(sandbox, str):
                sandbox = sandbox.lower() not in {"0", "false", "no", "off"}
            return PayPalPaymentProvider(
                client_id=getattr(django_settings, "PAYPAL_CLIENT_ID", ""),
                client_secret=getattr(django_settings, "PAYPAL_CLIENT_SECRET", "")
                or getattr(django_settings, "PAYPAL_SECRET", ""),
                webhook_id=getattr(django_settings, "PAYPAL_WEBHOOK_ID", None),
                sandbox=sandbox,
            )

        if provider == "square":
            from .providers.square import SquarePaymentProvider

            sandbox = getattr(django_settings, "SQUARE_SANDBOX", True)
            if isinstance(sandbox, str):
                sandbox = sandbox.lower() not in {"0", "false", "no", "off"}
            return SquarePaymentProvider(
                access_token=getattr(django_settings, "SQUARE_ACCESS_TOKEN", ""),
                location_id=getattr(django_settings, "SQUARE_LOCATION_ID", ""),
                webhook_signature_key=getattr(
                    django_settings, "SQUARE_WEBHOOK_SIGNATURE_KEY", None
                ),
                webhook_notification_url=getattr(
                    django_settings, "SQUARE_WEBHOOK_NOTIFICATION_URL", None
                ),
                sandbox=sandbox,
                api_version=getattr(django_settings, "SQUARE_API_VERSION", "2026-05-20"),
            )

    if provider == "stripe":
        from .providers.stripe import StripePaymentProvider

        return StripePaymentProvider()

    raise ValueError(f"Unknown Payment Provider: {provider}")
