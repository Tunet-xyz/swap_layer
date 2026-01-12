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

        stripe.api_key = secret_key
        self.secret_key = secret_key
        self.publishable_key = publishable_key or getattr(settings, "STRIPE_PUBLISHABLE_KEY", None)
        self.webhook_secret = webhook_secret or getattr(settings, "STRIPE_WEBHOOK_SECRET", None)

    def get_vendor_client(self) -> Any:
        """
        Return the stripe module for direct access.
        Useful for accessing Stripe-specific features not covered by the abstraction.
        """
        return stripe

    def _handle_stripe_error(self, e: Exception) -> None:
        """Convert Stripe exceptions to standard PaymentErrors."""
        if isinstance(e, stripe.error.CardError):
            raise PaymentDeclinedError(f"Payment declined: {e.user_message}") from e
        elif isinstance(e, stripe.error.InvalidRequestError):
            # Check if it's a 404-like error
            if "No such" in str(e):
                raise ResourceNotFoundError(str(e)) from e
            raise PaymentValidationError(f"Invalid request: {str(e)}") from e
        elif isinstance(e, stripe.error.AuthenticationError):
            raise PaymentConnectionError("Authentication failed. Check API keys.") from e
        elif isinstance(e, stripe.error.APIConnectionError):
            raise PaymentConnectionError("Network error connecting to Stripe.") from e
        elif isinstance(e, stripe.error.StripeError):
            raise PaymentError(f"Stripe error: {str(e)}") from e
        else:
            raise PaymentError(f"Unexpected error: {str(e)}") from e

    # Customer Management
    def create_customer(
        self, email: str, name: str | None = None, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a Stripe customer."""
        try:
            params = {"email": email}
            if name:
                params["name"] = name
            if metadata:
                params["metadata"] = metadata

            customer = stripe.Customer.create(**params)

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
            customer = stripe.Customer.retrieve(customer_id)

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
            params = {}
            if email:
                params["email"] = email
            if name:
                params["name"] = name
            if metadata:
                params["metadata"] = metadata

            customer = stripe.Customer.modify(customer_id, **params)

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
            result = stripe.Customer.delete(customer_id)

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
            params = {
                "customer": customer_id,
                "items": [{"price": price_id}],
            }
            if metadata:
                params["metadata"] = metadata
            if trial_period_days:
                params["trial_period_days"] = trial_period_days

            subscription = stripe.Subscription.create(**params)

            return self._normalize_subscription(subscription)
        except Exception as e:
            self._handle_stripe_error(e)

    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        """Retrieve a Stripe subscription."""
        subscription = stripe.Subscription.retrieve(subscription_id)
        return self._normalize_subscription(subscription)

    def update_subscription(
        self,
        subscription_id: str,
        price_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update a Stripe subscription."""
        params = {}

        if price_id:
            # Get the subscription to find the item ID
            subscription = stripe.Subscription.retrieve(subscription_id)
            params["items"] = [
                {
                    "id": subscription["items"]["data"][0].id,
                    "price": price_id,
                }
            ]

        if metadata:
            params["metadata"] = metadata

        subscription = stripe.Subscription.modify(subscription_id, **params)
        return self._normalize_subscription(subscription)

    def cancel_subscription(
        self, subscription_id: str, at_period_end: bool = True
    ) -> dict[str, Any]:
        """Cancel a Stripe subscription."""
        if at_period_end:
            subscription = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
        else:
            subscription = stripe.Subscription.delete(subscription_id)

        return self._normalize_subscription(subscription)

    def list_subscriptions(
        self, customer_id: str, status: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """List Stripe subscriptions for a customer."""
        params = {
            "customer": customer_id,
            "limit": limit,
        }
        if status:
            params["status"] = status

        subscriptions = stripe.Subscription.list(**params)
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
        payment_method = stripe.PaymentMethod.attach(
            payment_method_id,
            customer=customer_id,
        )

        return self._normalize_payment_method(payment_method)

    def detach_payment_method(self, payment_method_id: str) -> dict[str, Any]:
        """Detach a payment method from a Stripe customer."""
        payment_method = stripe.PaymentMethod.detach(payment_method_id)

        return {
            "id": payment_method.id,
            "customer_id": payment_method.customer,
        }

    def list_payment_methods(
        self, customer_id: str, method_type: str | None = None
    ) -> list[dict[str, Any]]:
        """List payment methods for a Stripe customer."""
        params = {
            "customer": customer_id,
            "type": method_type or "card",
        }

        payment_methods = stripe.PaymentMethod.list(**params)
        return [self._normalize_payment_method(pm) for pm in payment_methods.data]

    def set_default_payment_method(
        self, customer_id: str, payment_method_id: str
    ) -> dict[str, Any]:
        """Set the default payment method for a Stripe customer."""
        customer = stripe.Customer.modify(
            customer_id,
            invoice_settings={
                "default_payment_method": payment_method_id,
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
        params = {
            "amount": int(amount),  # Stripe expects amount in cents
            "currency": currency,
        }

        if customer_id:
            params["customer"] = customer_id
        if payment_method_id:
            params["payment_method"] = payment_method_id
        if metadata:
            params["metadata"] = metadata

        payment_intent = stripe.PaymentIntent.create(**params)

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
        params = {}
        if payment_method_id:
            params["payment_method"] = payment_method_id

        payment_intent = stripe.PaymentIntent.confirm(payment_intent_id, **params)

        return {
            "id": payment_intent.id,
            "status": payment_intent.status,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency,
        }

    def get_payment_intent(self, payment_intent_id: str) -> dict[str, Any]:
        """Retrieve a Stripe payment intent."""
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

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
        params = {
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

        session = stripe.checkout.Session.create(**params)

        return {
            "id": session.id,
            "url": session.url,
            "customer_id": session.customer,
            "mode": session.mode,
            "payment_status": session.payment_status,
        }

    def get_checkout_session(self, session_id: str) -> dict[str, Any]:
        """Retrieve a Stripe checkout session."""
        session = stripe.checkout.Session.retrieve(session_id)

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
        invoice = stripe.Invoice.retrieve(invoice_id)

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
        invoices = stripe.Invoice.list(customer=customer_id, limit=limit)

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
            event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
            return {
                "type": event["type"],
                "data": event["data"]["object"],
                "id": event["id"],
            }
        except ValueError as e:
            # Invalid payload
            raise ValueError(f"Invalid payload: {e}")
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            raise ValueError(f"Invalid signature: {e}")
