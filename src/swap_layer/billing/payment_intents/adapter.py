from abc import abstractmethod
from decimal import Decimal
from typing import Any


class PaymentAdapter:
    """
    Abstract base class for payment operations.
    This subdomain handles payment methods, payment intents, checkout sessions,
    invoices, and webhooks.
    """

    # Payment Methods
    @abstractmethod
    def attach_payment_method(self, customer_id: str, payment_method_id: str) -> dict[str, Any]:
        """
        Attach a payment method to a customer.

        Returns:
            Dict with keys: id, customer_id, type, card/bank details
        """
        pass

    @abstractmethod
    def detach_payment_method(self, payment_method_id: str) -> dict[str, Any]:
        """
        Detach a payment method from a customer.

        Returns:
            Dict with keys: id, customer_id
        """
        pass

    @abstractmethod
    def list_payment_methods(
        self, customer_id: str, method_type: str | None = None
    ) -> list[dict[str, Any]]:
        """
        List payment methods for a customer.

        Args:
            customer_id: The customer ID
            method_type: Optional type filter (card, bank_account, etc.)

        Returns:
            List of payment method dicts
        """
        pass

    @abstractmethod
    def set_default_payment_method(
        self, customer_id: str, payment_method_id: str
    ) -> dict[str, Any]:
        """
        Set the default payment method for a customer.

        Returns:
            Dict with updated customer data
        """
        pass

    # One-time Payments
    @abstractmethod
    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        customer_id: str | None = None,
        payment_method_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Create a payment intent for a one-time payment."""
        pass

    @abstractmethod
    def confirm_payment_intent(
        self, payment_intent_id: str, payment_method_id: str | None = None
    ) -> dict[str, Any]:
        """
        Confirm a payment intent.

        Returns:
            Dict with keys: id, status, amount, currency
        """
        pass

    @abstractmethod
    def get_payment_intent(self, payment_intent_id: str) -> dict[str, Any]:
        """
        Retrieve payment intent details.

        Returns:
            Dict with keys: id, amount, currency, status
        """
        pass

    # Checkout Sessions (for hosted checkout pages)
    @abstractmethod
    def create_checkout_session(
        self,
        customer_id: str | None = None,
        price_id: str | None = None,
        success_url: str | None = None,
        cancel_url: str | None = None,
        mode: str = "subscription",
        metadata: dict[str, Any] | None = None,
        line_items: list[dict[str, Any]] | None = None,
        quantity: int = 1,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Create a checkout session for hosted payment page."""
        pass

    @abstractmethod
    def get_checkout_session(self, session_id: str) -> dict[str, Any]:
        """
        Retrieve checkout session details.

        Returns:
            Dict with keys: id, customer_id, payment_status, mode
        """
        pass

    # Invoices
    @abstractmethod
    def get_invoice(self, invoice_id: str) -> dict[str, Any]:
        """
        Retrieve invoice details.

        Returns:
            Dict with keys: id, customer_id, amount_due, amount_paid, status
        """
        pass

    @abstractmethod
    def list_invoices(self, customer_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        List invoices for a customer.

        Returns:
            List of invoice dicts
        """
        pass

    # Billing Portal
    @abstractmethod
    def create_billing_portal_session(
        self, customer_id: str, return_url: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        pass

    # Refunds
    @abstractmethod
    def create_refund(
        self,
        payment_intent_id: str | None = None,
        charge_id: str | None = None,
        amount: Decimal | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_refund(self, refund_id: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def list_refunds(
        self,
        payment_intent_id: str | None = None,
        charge_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        pass

    # Metered Usage
    @abstractmethod
    def create_meter(self, display_name: str, event_name: str, **kwargs: Any) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_meter(self, meter_id: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def list_meters(self, limit: int = 10, status: str | None = None) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def create_meter_event(
        self,
        event_name: str,
        customer_id: str | None = None,
        value: Decimal | int | str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def record_usage(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        pass

    @abstractmethod
    def create_meter_event_session(self) -> dict[str, Any]:
        pass

    @abstractmethod
    def create_meter_event_stream(
        self, events: list[dict[str, Any]], authentication_token: str | None = None
    ) -> dict[str, Any]:
        pass

    # Discounts and Tax
    @abstractmethod
    def create_coupon(self, **kwargs: Any) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_coupon(self, coupon_id: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def delete_coupon(self, coupon_id: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def create_promotion_code(self, coupon_id: str, **kwargs: Any) -> dict[str, Any]:
        pass

    @abstractmethod
    def create_tax_rate(
        self, display_name: str, percentage: Decimal, **kwargs: Any
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def list_tax_rates(self, active: bool | None = None, limit: int = 10) -> list[dict[str, Any]]:
        pass

    # Invoice Actions
    @abstractmethod
    def create_invoice(self, customer_id: str, **kwargs: Any) -> dict[str, Any]:
        pass

    @abstractmethod
    def finalize_invoice(self, invoice_id: str, **kwargs: Any) -> dict[str, Any]:
        pass

    @abstractmethod
    def pay_invoice(self, invoice_id: str, **kwargs: Any) -> dict[str, Any]:
        pass

    @abstractmethod
    def void_invoice(self, invoice_id: str, **kwargs: Any) -> dict[str, Any]:
        pass

    # Webhooks
    def create_webhook_endpoint(
        self,
        url: str,
        enabled_events: list[str],
        *,
        description: str | None = None,
        metadata: dict[str, str] | None = None,
        connect: bool = False,
        api_version: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Register a provider webhook destination.

        Providers that return a signing secret should include it only in this
        creation result; callers must move it directly to an approved secret
        store and must not log or persist the result.
        """
        raise NotImplementedError("Webhook endpoint provisioning is not supported by this provider")

    def get_webhook_endpoint(self, endpoint_id: str) -> dict[str, Any]:
        """Retrieve non-secret webhook endpoint configuration."""
        raise NotImplementedError("Webhook endpoint discovery is not supported by this provider")

    def list_webhook_endpoints(self, limit: int = 100) -> list[dict[str, Any]]:
        """List non-secret webhook endpoint configuration."""
        raise NotImplementedError("Webhook endpoint discovery is not supported by this provider")

    def update_webhook_endpoint(
        self,
        endpoint_id: str,
        *,
        url: str | None = None,
        enabled_events: list[str] | None = None,
        description: str | None = None,
        metadata: dict[str, str] | None = None,
        disabled: bool | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Update a provider webhook destination without rotating its secret."""
        raise NotImplementedError("Webhook endpoint updates are not supported by this provider")

    def delete_webhook_endpoint(self, endpoint_id: str) -> dict[str, Any]:
        """Delete a provider webhook destination explicitly."""
        raise NotImplementedError("Webhook endpoint deletion is not supported by this provider")

    @abstractmethod
    def verify_webhook_signature(
        self, payload: bytes, signature: str, webhook_secret: str | None = None, thin: bool = False
    ) -> dict[str, Any]:
        """
        Verify and parse a webhook payload.

        Returns:
            Dict with keys: type, data (the event object)
        """
        pass

    @abstractmethod
    def dispatch_webhook_event(
        self,
        event: dict[str, Any],
        handlers: dict[str, Any],
        processed_event_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        pass
