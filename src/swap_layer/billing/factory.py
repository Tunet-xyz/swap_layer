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
    # Get provider from SwapLayerSettings
    settings = get_swaplayer_settings()

    if settings.billing:
        provider = settings.billing.provider
        # Pass Stripe config from SwapLayerSettings if available
        if provider == "stripe" and settings.billing.stripe:
            from .providers.stripe import StripePaymentProvider

            return StripePaymentProvider(
                secret_key=settings.billing.stripe.secret_key,
                publishable_key=settings.billing.stripe.publishable_key,
                webhook_secret=settings.billing.stripe.webhook_secret,
            )
    else:
        # Fallback to legacy Django settings for backward compatibility
        from django.conf import settings as django_settings

        provider = getattr(django_settings, "PAYMENT_PROVIDER", "stripe")

    if provider == "stripe":
        from .providers.stripe import StripePaymentProvider

        return StripePaymentProvider()
    # Add other providers here as they are implemented
    # elif provider == 'paypal':
    #     return PayPalPaymentProvider()
    # elif provider == 'square':
    #     return SquarePaymentProvider()
    else:
        raise ValueError(f"Unknown Payment Provider: {provider}")
