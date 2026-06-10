from decimal import Decimal
from typing import Any

import stripe
from django.conf import settings

from ..adapter import (
    PaymentConnectionError,
    PaymentDeclinedError,
    PaymentError,
    PaymentProviderAdapter,
    PaymentValidationError,
    ResourceNotFoundError,
)


class StripePaymentProvider(PaymentProviderAdapter):
    """
    Stripe implementation of the PaymentProviderAdapter.

    Uses the StripeClient service-based pattern (v8+) instead of the deprecated
    global stripe.api_key + resource class methods.
    """

    def __init__(
        self,
        secret_key: str | None = None,
        publishable_key: str | None = None,
        webhook_secret: str | None = None,
    ):
        """
        Initialize Stripe payment provider.

        Args:
            secret_key: Stripe secret key (falls back to settings.STRIPE_SECRET_KEY)
            publishable_key: Stripe publishable key (falls back to settings.STRIPE_PUBLISHABLE_KEY)
            webhook_secret: Stripe webhook secret (falls back to settings.STRIPE_WEBHOOK_SECRET)
        """
        # Use provided config or fallback to Django settings for backward compatibility
        if secret_key is None:
            secret_key = getattr(settings, "STRIPE_SECRET_KEY", None)

        if not secret_key:
            raise ValueError("STRIPE_SECRET_KEY is required but not configured")

        self._client = stripe.StripeClient(secret_key, max_network_retries=2)
        self.secret_key = secret_key
        self.publishable_key = publishable_key or getattr(settings, "STRIPE_PUBLISHABLE_KEY", None)
        self.webhook_secret = webhook_secret or getattr(settings, "STRIPE_WEBHOOK_SECRET", None)

    def get_vendor_client(self) -> Any:
        """
        Return the StripeClient instance for direct access.
        Useful for accessing Stripe-specific features not covered by the abstraction.
        """
        return self._client

    def _handle_stripe_error(self, e: Exception) -> None:
        """Convert Stripe exceptions to standard PaymentErrors."""
        if isinstance(e, stripe.CardError):
            raise PaymentDeclinedError(f"Payment declined: {e.user_message}") from e
        elif isinstance(e, stripe.InvalidRequestError):
            # Check if it's a 404-like error
            if "No such" in str(e):
                raise ResourceNotFoundError(str(e)) from e
            raise PaymentValidationError(f"Invalid request: {str(e)}") from e
        elif isinstance(e, stripe.AuthenticationError):
            raise PaymentConnectionError("Authentication failed. Check API keys.") from e
        elif isinstance(e, stripe.APIConnectionError):
            raise PaymentConnectionError("Network error connecting to Stripe.") from e
        elif isinstance(e, stripe.StripeError):
            raise PaymentError(f"Stripe error: {str(e)}") from e
        else:
            raise PaymentError(f"Unexpected error: {str(e)}") from e

    # Customer Management
    def create_customer(
        self, email: str, name: str | None = None, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a Stripe customer."""
        try:
            params: dict[str, Any] = {"email": email}
            if name:
                params["name"] = name
            if metadata:
                params["metadata"] = metadata

            customer = self._client.v1.customers.create(params=params)

            return {
                "id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "created": customer.created,
                "metadata": customer.metadata,
            }
        except Exception as e:
            self._handle_stripe_error(e)

    def get_customer(self, customer_id: str) -> dict[str, Any]:
        """Retrieve a Stripe customer."""
        try:
            customer = self._client.v1.customers.retrieve(customer_id)

            return {
                "id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "metadata": customer.metadata,
                "default_payment_method": customer.invoice_settings.default_payment_method
                if customer.invoice_settings
                else None,
            }
        except Exception as e:
            self._handle_stripe_error(e)

    def update_customer(
        self,
        customer_id: str,
        email: str | None = None,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update a Stripe customer."""
        try:
            params: dict[str, Any] = {}
            if email:
                params["email"] = email
            if name:
                params["name"] = name
            if metadata:
                params["metadata"] = metadata

            customer = self._client.v1.customers.update(customer_id, params=params)

            return {
                "id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "metadata": customer.metadata,
            }
        except Exception as e:
            self._handle_stripe_error(e)

    def delete_customer(self, customer_id: str) -> dict[str, Any]:
        """Delete a Stripe customer."""
        try:
            result = self._client.v1.customers.delete(customer_id)

            return {
                "id": result.id,
                "deleted": result.deleted,
            }
        except Exception as e:
            self._handle_stripe_error(e)

    # Subscription Management
    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        metadata: dict[str, Any] | None = None,
        trial_period_days: int | None = None,
    ) -> dict[str, Any]:
        """Create a Stripe subscription."""
        try:
            params: dict[str, Any] = {
                "customer": customer_id,
                "items": [{"price": price_id}],
            }
            if metadata:
                params["metadata"] = metadata
            if trial_period_days:
                params["trial_period_days"] = trial_period_days

            subscription = self._client.v1.subscriptions.create(params=params)

            return self._normalize_subscription(subscription)
        except Exception as e:
            self._handle_stripe_error(e)

    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        """Retrieve a Stripe subscription."""
        subscription = self._client.v1.subscriptions.retrieve(subscription_id)
        return self._normalize_subscription(subscription)

    def update_subscription(
        self,
        subscription_id: str,
        price_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update a Stripe subscription."""
        params: dict[str, Any] = {}

        if price_id:
            # Get the subscription to find the item ID
            subscription = self._client.v1.subscriptions.retrieve(subscription_id)
            params["items"] = [
                {
                    "id": subscription.items.data[0].id,
                    "price": price_id,
                }
            ]

        if metadata:
            params["metadata"] = metadata

        subscription = self._client.v1.subscriptions.update(subscription_id, params=params)
        return self._normalize_subscription(subscription)

    def cancel_subscription(
        self, subscription_id: str, at_period_end: bool = True
    ) -> dict[str, Any]:
        """Cancel a Stripe subscription."""
        if at_period_end:
            subscription = self._client.v1.subscriptions.update(
                subscription_id, params={"cancel_at_period_end": True}
            )
        else:
            subscription = self._client.v1.subscriptions.cancel(subscription_id)

        return self._normalize_subscription(subscription)

    def list_subscriptions(
        self, customer_id: str, status: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """List Stripe subscriptions for a customer."""
        params: dict[str, Any] = {
            "customer": customer_id,
            "limit": limit,
        }
        if status:
            params["status"] = status

        subscriptions = self._client.v1.subscriptions.list(params=params)
        return [self._normalize_subscription(sub) for sub in subscriptions.data]

    def _normalize_subscription(self, subscription) -> dict[str, Any]:
        """Normalize Stripe subscription data to standard format."""
        items = []
        if hasattr(subscription, "items") and subscription.items:
            for item in subscription.items.data:
                items.append(
                    {
                        "id": item.id,
                        "price_id": item.price.id,
                        "quantity": item.quantity,
                    }
                )

        return {
            "id": subscription.id,
            "customer_id": subscription.customer,
            "status": subscription.status,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "canceled_at": subscription.canceled_at,
            "items": items,
            "metadata": subscription.metadata if hasattr(subscription, "metadata") else {},
        }

    # Payment Methods
    def attach_payment_method(self, customer_id: str, payment_method_id: str) -> dict[str, Any]:
        """Attach a payment method to a Stripe customer."""
        payment_method = self._client.v1.payment_methods.attach(
            payment_method_id,
            params={"customer": customer_id},
        )

        return self._normalize_payment_method(payment_method)

    def detach_payment_method(self, payment_method_id: str) -> dict[str, Any]:
        """Detach a payment method from a Stripe customer."""
        payment_method = self._client.v1.payment_methods.detach(payment_method_id)

        return {
            "id": payment_method.id,
            "customer_id": payment_method.customer,
        }

    def list_payment_methods(
        self, customer_id: str, method_type: str | None = None
    ) -> list[dict[str, Any]]:
        """List payment methods for a Stripe customer."""
        params: dict[str, Any] = {
            "customer": customer_id,
            "type": method_type or "card",
        }

        payment_methods = self._client.v1.payment_methods.list(params=params)
        return [self._normalize_payment_method(pm) for pm in payment_methods.data]

    def set_default_payment_method(
        self, customer_id: str, payment_method_id: str
    ) -> dict[str, Any]:
        """Set the default payment method for a Stripe customer."""
        customer = self._client.v1.customers.update(
            customer_id,
            params={
                "invoice_settings": {
                    "default_payment_method": payment_method_id,
                },
            },
        )

        return {
            "id": customer.id,
            "default_payment_method": customer.invoice_settings.default_payment_method,
        }

    def _normalize_payment_method(self, payment_method) -> dict[str, Any]:
        """Normalize Stripe payment method data to standard format."""
        result = {
            "id": payment_method.id,
            "customer_id": payment_method.customer,
            "type": payment_method.type,
        }

        if payment_method.type == "card" and hasattr(payment_method, "card"):
            result["card"] = {
                "brand": payment_method.card.brand,
                "last4": payment_method.card.last4,
                "exp_month": payment_method.card.exp_month,
                "exp_year": payment_method.card.exp_year,
            }

        return result

    # One-time Payments
    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        customer_id: str | None = None,
        payment_method_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a Stripe payment intent."""
        params: dict[str, Any] = {
            "amount": int(amount),  # Stripe expects amount in cents
            "currency": currency,
        }

        if customer_id:
            params["customer"] = customer_id
        if payment_method_id:
            params["payment_method"] = payment_method_id
        if metadata:
            params["metadata"] = metadata

        payment_intent = self._client.v1.payment_intents.create(params=params)

        return {
            "id": payment_intent.id,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency,
            "status": payment_intent.status,
            "client_secret": payment_intent.client_secret,
            "metadata": payment_intent.metadata,
        }

    def confirm_payment_intent(
        self, payment_intent_id: str, payment_method_id: str | None = None
    ) -> dict[str, Any]:
        """Confirm a Stripe payment intent."""
        params: dict[str, Any] = {}
        if payment_method_id:
            params["payment_method"] = payment_method_id

        payment_intent = self._client.v1.payment_intents.confirm(
            payment_intent_id, params=params if params else None
        )

        return {
            "id": payment_intent.id,
            "status": payment_intent.status,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency,
        }

    def get_payment_intent(self, payment_intent_id: str) -> dict[str, Any]:
        """Retrieve a Stripe payment intent."""
        payment_intent = self._client.v1.payment_intents.retrieve(payment_intent_id)

        return {
            "id": payment_intent.id,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency,
            "status": payment_intent.status,
            "metadata": payment_intent.metadata,
        }

    # Checkout Sessions
    def create_checkout_session(
        self,
        customer_id: str | None = None,
        price_id: str | None = None,
        success_url: str | None = None,
        cancel_url: str | None = None,
        mode: str = "subscription",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a Stripe checkout session."""
        params: dict[str, Any] = {
            "mode": mode,
        }

        if customer_id:
            params["customer"] = customer_id

        if price_id:
            params["line_items"] = [{"price": price_id, "quantity": 1}]

        if success_url:
            params["success_url"] = success_url
        if cancel_url:
            params["cancel_url"] = cancel_url
        if metadata:
            params["metadata"] = metadata

        session = self._client.v1.checkout.sessions.create(params=params)

        return {
            "id": session.id,
            "url": session.url,
            "customer_id": session.customer,
            "mode": session.mode,
            "payment_status": session.payment_status,
        }

    def get_checkout_session(self, session_id: str) -> dict[str, Any]:
        """Retrieve a Stripe checkout session."""
        session = self._client.v1.checkout.sessions.retrieve(session_id)

        return {
            "id": session.id,
            "customer_id": session.customer,
            "payment_status": session.payment_status,
            "mode": session.mode,
            "subscription_id": session.subscription if hasattr(session, "subscription") else None,
        }

    # Invoices
    def get_invoice(self, invoice_id: str) -> dict[str, Any]:
        """Retrieve a Stripe invoice."""
        invoice = self._client.v1.invoices.retrieve(invoice_id)

        return {
            "id": invoice.id,
            "customer_id": invoice.customer,
            "amount_due": invoice.amount_due,
            "amount_paid": invoice.amount_paid,
            "status": invoice.status,
            "created": invoice.created,
            "currency": invoice.currency,
        }

    def list_invoices(self, customer_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """List Stripe invoices for a customer."""
        invoices = self._client.v1.invoices.list(params={"customer": customer_id, "limit": limit})

        return [
            {
                "id": invoice.id,
                "customer_id": invoice.customer,
                "amount_due": invoice.amount_due,
                "amount_paid": invoice.amount_paid,
                "status": invoice.status,
                "created": invoice.created,
                "currency": invoice.currency,
            }
            for invoice in invoices.data
        ]

    # Webhooks
    def verify_webhook_signature(
        self, payload: bytes, signature: str, webhook_secret: str
    ) -> dict[str, Any]:
        """Verify and parse a Stripe webhook payload."""
        try:
            event = self._client.construct_event(payload, signature, webhook_secret)
            return {
                "type": event.type,
                "data": event.data.object,
                "id": event.id,
            }
        except ValueError as e:
            # Invalid payload
            raise ValueError(f"Invalid payload: {e}")
        except stripe.SignatureVerificationError as e:
            # Invalid signature
            raise ValueError(f"Invalid signature: {e}")
