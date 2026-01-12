from abc import ABC, abstractmethod
from typing import Any

# Import subdomain adapters
from swap_layer.billing.customers.adapter import CustomerAdapter
from swap_layer.billing.payment_intents.adapter import PaymentAdapter
from swap_layer.billing.products.adapter import ProductAdapter
from swap_layer.billing.subscriptions.adapter import SubscriptionAdapter


class PaymentError(Exception):
    """Base exception for all payment related errors."""

    pass


class PaymentValidationError(PaymentError):
    """Raised when input data is invalid (e.g. invalid email, negative amount)."""

    pass


class PaymentDeclinedError(PaymentError):
    """Raised when the payment was declined by the processor."""

    pass


class PaymentConnectionError(PaymentError):
    """Raised when connection to the payment provider fails."""

    pass


class ResourceNotFoundError(PaymentError):
    """Raised when a requested resource (customer, subscription) is not found."""

    pass


class PaymentProviderAdapter(
    ABC, CustomerAdapter, SubscriptionAdapter, PaymentAdapter, ProductAdapter
):
    """
    Abstract base class for Payment Providers (Stripe, PayPal, Square, etc.)
    This ensures we can switch providers without rewriting the application logic.

    This adapter now composes functionality from subdomain adapters:
    - CustomerAdapter: Customer management operations
    - SubscriptionAdapter: Subscription lifecycle operations
    - PaymentAdapter: Payment intents, methods, checkout, invoices, webhooks
    - ProductAdapter: Product and pricing management (placeholder)
    """

    @abstractmethod
    def get_vendor_client(self) -> Any:
        """
        Return the underlying vendor client/SDK for advanced usage.
        Use this escape hatch when you need to access provider-specific features
        that are not exposed by the abstraction layer.
        """
        pass
