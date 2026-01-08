from django.conf import settings

from .adapter import PaymentProviderAdapter
from .providers.stripe import StripePaymentProvider


def get_payment_provider() -> PaymentProviderAdapter:
    """
    Factory function to return the configured Payment Provider.
    This allows switching vendors by changing the PAYMENT_PROVIDER Django setting.

    Returns:
        PaymentProviderAdapter: The configured payment provider instance

    Raises:
        ValueError: If the provider is not supported or not configured
    """
    provider = getattr(settings, "PAYMENT_PROVIDER", "stripe")

    if provider == "stripe":
        return StripePaymentProvider()
    # Add other providers here as they are implemented
    # elif provider == 'paypal':
    #     return PayPalPaymentProvider()
    # elif provider == 'square':
    #     return SquarePaymentProvider()
    else:
        raise ValueError(f"Unknown Payment Provider: {provider}")
