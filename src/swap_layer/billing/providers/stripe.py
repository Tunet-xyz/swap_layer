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
        if secret_key is None and settings.configured:
            secret_key = getattr(settings, "STRIPE_SECRET_KEY", None)

        if not secret_key:
            raise ValueError("STRIPE_SECRET_KEY is required but not configured")

        self._client = stripe.StripeClient(secret_key, max_network_retries=2)
        self.secret_key = secret_key
        self.publishable_key = publishable_key or (
            getattr(settings, "STRIPE_PUBLISHABLE_KEY", None) if settings.configured else None
        )
        self.webhook_secret = webhook_secret or (
            getattr(settings, "STRIPE_WEBHOOK_SECRET", None) if settings.configured else None
        )

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
        price_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        trial_period_days: int | None = None,
        items: list[dict[str, Any]] | None = None,
        quantity: int | None = None,
        payment_behavior: str | None = None,
        proration_behavior: str | None = None,
        collection_method: str | None = None,
        default_payment_method: str | None = None,
        billing_cycle_anchor: int | None = None,
        automatic_tax: dict[str, Any] | None = None,
        discounts: list[dict[str, Any]] | None = None,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Create a Stripe subscription."""
        try:
            subscription_items = items or []
            if price_id:
                item: dict[str, Any] = {"price": price_id}
                if quantity is not None:
                    item["quantity"] = quantity
                subscription_items.append(item)
            if not subscription_items:
                raise PaymentValidationError("Either price_id or items is required")

            params: dict[str, Any] = {
                "customer": customer_id,
                "items": subscription_items,
            }
            optional_params = {
                "metadata": metadata,
                "trial_period_days": trial_period_days,
                "payment_behavior": payment_behavior,
                "proration_behavior": proration_behavior,
                "collection_method": collection_method,
                "default_payment_method": default_payment_method,
                "billing_cycle_anchor": billing_cycle_anchor,
                "automatic_tax": automatic_tax,
                "discounts": discounts,
            }
            params.update(
                {key: value for key, value in optional_params.items() if value is not None}
            )
            params.update(extra_params)

            subscription = self._client.v1.subscriptions.create(
                params=params,
                options=self._request_options(idempotency_key),
            )

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
        items: list[dict[str, Any]] | None = None,
        quantity: int | None = None,
        proration_behavior: str | None = None,
        payment_behavior: str | None = None,
        default_payment_method: str | None = None,
        cancel_at_period_end: bool | None = None,
        automatic_tax: dict[str, Any] | None = None,
        discounts: list[dict[str, Any]] | None = None,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Update a Stripe subscription."""
        params: dict[str, Any] = {}

        if items is not None:
            params["items"] = items
        elif price_id:
            subscription = self._client.v1.subscriptions.retrieve(subscription_id)
            item: dict[str, Any] = {
                "id": subscription.items.data[0].id,
                "price": price_id,
            }
            if quantity is not None:
                item["quantity"] = quantity
            params["items"] = [item]

        optional_params = {
            "metadata": metadata,
            "proration_behavior": proration_behavior,
            "payment_behavior": payment_behavior,
            "default_payment_method": default_payment_method,
            "cancel_at_period_end": cancel_at_period_end,
            "automatic_tax": automatic_tax,
            "discounts": discounts,
        }
        params.update({key: value for key, value in optional_params.items() if value is not None})
        params.update(extra_params)

        subscription = self._client.v1.subscriptions.update(
            subscription_id,
            params=params,
            options=self._request_options(idempotency_key),
        )
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

    def _request_options(self, idempotency_key: str | None = None) -> dict[str, Any] | None:
        if not idempotency_key:
            return None
        return {"idempotency_key": idempotency_key}

    @staticmethod
    def _auto_paging_items(collection: Any) -> list[Any]:
        """Consume every object from a Stripe ListObject, with a safe test fallback."""
        auto_paging_iter = getattr(collection, "auto_paging_iter", None)
        if callable(auto_paging_iter):
            return list(auto_paging_iter())
        return list(getattr(collection, "data", []))

    @staticmethod
    def _catalog_value(value: Any, name: str, default: Any = None) -> Any:
        if isinstance(value, dict):
            return value.get(name, default)
        return getattr(value, name, default)

    @staticmethod
    def _catalog_dict(value: Any) -> dict[str, Any]:
        """Normalize plain mappings and StripeObject containers to a dictionary."""
        if isinstance(value, dict):
            return dict(value)
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            normalized = to_dict()
            return dict(normalized) if isinstance(normalized, dict) else {}
        return {}

    @classmethod
    def _catalog_id(cls, value: Any) -> str | None:
        if isinstance(value, str):
            return value
        identifier = cls._catalog_value(value, "id")
        return identifier if isinstance(identifier, str) else None

    # One-time Payments
    def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        customer_id: str | None = None,
        payment_method_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        automatic_payment_methods: dict[str, Any] | None = None,
        capture_method: str | None = None,
        setup_future_usage: str | None = None,
        receipt_email: str | None = None,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Create a Stripe payment intent."""
        params: dict[str, Any] = {
            "amount": int(amount),
            "currency": currency,
        }

        optional_params = {
            "customer": customer_id,
            "payment_method": payment_method_id,
            "metadata": metadata,
            "automatic_payment_methods": automatic_payment_methods,
            "capture_method": capture_method,
            "setup_future_usage": setup_future_usage,
            "receipt_email": receipt_email,
        }
        params.update({key: value for key, value in optional_params.items() if value is not None})
        params.update(extra_params)

        payment_intent = self._client.v1.payment_intents.create(
            params=params,
            options=self._request_options(idempotency_key),
        )

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
        line_items: list[dict[str, Any]] | None = None,
        quantity: int = 1,
        customer_email: str | None = None,
        client_reference_id: str | None = None,
        allow_promotion_codes: bool | None = None,
        automatic_tax: dict[str, Any] | None = None,
        tax_id_collection: dict[str, Any] | None = None,
        consent_collection: dict[str, Any] | None = None,
        custom_fields: list[dict[str, Any]] | None = None,
        custom_text: dict[str, Any] | None = None,
        discounts: list[dict[str, Any]] | None = None,
        subscription_data: dict[str, Any] | None = None,
        payment_intent_data: dict[str, Any] | None = None,
        invoice_creation: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Create a Stripe checkout session."""
        params: dict[str, Any] = {"mode": mode}

        if customer_id:
            params["customer"] = customer_id
        if price_id:
            params["line_items"] = [{"price": price_id, "quantity": quantity}]
        if line_items is not None:
            params["line_items"] = line_items

        optional_params = {
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": metadata,
            "customer_email": customer_email,
            "client_reference_id": client_reference_id,
            "allow_promotion_codes": allow_promotion_codes,
            "automatic_tax": automatic_tax,
            "tax_id_collection": tax_id_collection,
            "consent_collection": consent_collection,
            "custom_fields": custom_fields,
            "custom_text": custom_text,
            "discounts": discounts,
            "subscription_data": subscription_data,
            "payment_intent_data": payment_intent_data,
            "invoice_creation": invoice_creation,
        }
        params.update({key: value for key, value in optional_params.items() if value is not None})
        params.update(extra_params)

        session = self._client.v1.checkout.sessions.create(
            params=params,
            options=self._request_options(idempotency_key),
        )

        return self._normalize_checkout_session(session)

    def get_checkout_session(self, session_id: str) -> dict[str, Any]:
        """Retrieve a Stripe checkout session."""
        session = self._client.v1.checkout.sessions.retrieve(session_id)
        return self._normalize_checkout_session(session)

    def _normalize_checkout_session(self, session) -> dict[str, Any]:
        return {
            "id": session.id,
            "url": getattr(session, "url", None),
            "customer_id": session.customer,
            "mode": session.mode,
            "payment_status": session.payment_status,
            "subscription_id": session.subscription if hasattr(session, "subscription") else None,
            "payment_intent_id": session.payment_intent
            if hasattr(session, "payment_intent")
            else None,
            "metadata": session.metadata if hasattr(session, "metadata") else {},
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

    def pause_subscription(
        self,
        subscription_id: str,
        behavior: str = "void",
        resumes_at: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Pause collection for a subscription."""
        params: dict[str, Any] = {"pause_collection": {"behavior": behavior}}
        if resumes_at is not None:
            params["pause_collection"]["resumes_at"] = resumes_at
        subscription = self._client.v1.subscriptions.update(
            subscription_id,
            params=params,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_subscription(subscription)

    def resume_subscription(
        self,
        subscription_id: str,
        billing_cycle_anchor: str | None = None,
        proration_behavior: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Resume a paused subscription."""
        params = {
            key: value
            for key, value in {
                "billing_cycle_anchor": billing_cycle_anchor,
                "proration_behavior": proration_behavior,
            }.items()
            if value is not None
        }
        subscription = self._client.v1.subscriptions.resume(
            subscription_id,
            params=params or None,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_subscription(subscription)

    # Product and Pricing
    def create_product(
        self,
        name: str,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        active: bool | None = None,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Create a product in Stripe."""
        params: dict[str, Any] = {"name": name}
        params.update(
            {
                key: value
                for key, value in {
                    "description": description,
                    "metadata": metadata,
                    "active": active,
                }.items()
                if value is not None
            }
        )
        params.update(extra_params)
        product = self._client.v1.products.create(
            params=params,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_product(product)

    def get_product(self, product_id: str) -> dict[str, Any]:
        """Retrieve a product from Stripe."""
        return self._normalize_product(self._client.v1.products.retrieve(product_id))

    def update_product(
        self,
        product_id: str,
        name: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        active: bool | None = None,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Update a product in Stripe."""
        params = {
            key: value
            for key, value in {
                "name": name,
                "description": description,
                "metadata": metadata,
                "active": active,
            }.items()
            if value is not None
        }
        params.update(extra_params)
        product = self._client.v1.products.update(
            product_id,
            params=params,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_product(product)

    def list_products(self, limit: int = 10, active: bool | None = None) -> list[dict[str, Any]]:
        """List products from Stripe."""
        params: dict[str, Any] = {"limit": limit}
        if active is not None:
            params["active"] = active
        products = self._client.v1.products.list(params=params)
        return [self._normalize_product(product) for product in products.data]

    def list_all_products(self, active: bool | None = None) -> list[dict[str, Any]]:
        """List the complete Stripe product catalog using SDK auto-pagination."""
        params: dict[str, Any] = {"limit": 100}
        if active is not None:
            params["active"] = active
        products = self._client.v1.products.list(params=params)
        return [self._normalize_product(product) for product in self._auto_paging_items(products)]

    def create_price(
        self,
        product_id: str,
        amount: Decimal,
        currency: str,
        recurring: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        lookup_key: str | None = None,
        nickname: str | None = None,
        tax_behavior: str | None = None,
        billing_scheme: str | None = None,
        tiers: list[dict[str, Any]] | None = None,
        transform_quantity: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Create a price for a product."""
        params: dict[str, Any] = {
            "product": product_id,
            "unit_amount": int(amount),
            "currency": currency,
        }
        optional_params = {
            "recurring": recurring,
            "metadata": metadata,
            "lookup_key": lookup_key,
            "nickname": nickname,
            "tax_behavior": tax_behavior,
            "billing_scheme": billing_scheme,
            "tiers": tiers,
            "transform_quantity": transform_quantity,
        }
        params.update({key: value for key, value in optional_params.items() if value is not None})
        params.update(extra_params)
        price = self._client.v1.prices.create(
            params=params,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_price(price)

    def get_price(self, price_id: str) -> dict[str, Any]:
        """Retrieve a price from Stripe."""
        return self._normalize_price(self._client.v1.prices.retrieve(price_id))

    def update_price(
        self,
        price_id: str,
        *,
        active: bool | None = None,
        metadata: dict[str, Any] | None = None,
        nickname: str | None = None,
        lookup_key: str | None = None,
        transfer_lookup_key: bool | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Update the mutable fields of a Stripe price."""
        params = {
            key: value
            for key, value in {
                "active": active,
                "metadata": metadata,
                "nickname": nickname,
                "lookup_key": lookup_key,
                "transfer_lookup_key": transfer_lookup_key,
            }.items()
            if value is not None
        }
        price = self._client.v1.prices.update(
            price_id,
            params=params,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_price(price)

    def replace_price(
        self,
        replaced_price_id: str,
        *,
        product_id: str,
        amount: Decimal,
        currency: str,
        lookup_key: str,
        recurring: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        nickname: str | None = None,
        tax_behavior: str | None = None,
        billing_scheme: str | None = None,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Create an immutable-price successor and transfer its stable lookup key.

        The previous price is deliberately left active. Archival and subscription
        migration require separate, explicit operations.
        """
        replacement = self.create_price(
            product_id=product_id,
            amount=amount,
            currency=currency,
            recurring=recurring,
            metadata=metadata,
            lookup_key=lookup_key,
            nickname=nickname,
            tax_behavior=tax_behavior,
            billing_scheme=billing_scheme,
            idempotency_key=idempotency_key,
            transfer_lookup_key=True,
            **extra_params,
        )
        replacement["replaces_price_id"] = replaced_price_id
        replacement["previous_price_archived"] = False
        return replacement

    def list_prices(
        self,
        product_id: str | None = None,
        limit: int = 10,
        active: bool | None = None,
        lookup_keys: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """List prices from Stripe."""
        params: dict[str, Any] = {"limit": limit}
        if product_id:
            params["product"] = product_id
        if active is not None:
            params["active"] = active
        if lookup_keys:
            params["lookup_keys"] = lookup_keys
        prices = self._client.v1.prices.list(params=params)
        return [self._normalize_price(price) for price in prices.data]

    def list_all_prices(
        self,
        product_id: str | None = None,
        active: bool | None = None,
        lookup_keys: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """List the complete Stripe price catalog using SDK auto-pagination."""
        params: dict[str, Any] = {"limit": 100}
        if product_id:
            params["product"] = product_id
        if active is not None:
            params["active"] = active
        if lookup_keys:
            params["lookup_keys"] = lookup_keys
        prices = self._client.v1.prices.list(params=params)
        return [self._normalize_price(price) for price in self._auto_paging_items(prices)]

    def _normalize_product(self, product) -> dict[str, Any]:
        metadata = self._catalog_value(product, "metadata", {})
        return {
            "id": self._catalog_value(product, "id"),
            "name": self._catalog_value(product, "name"),
            "description": self._catalog_value(product, "description"),
            "active": self._catalog_value(product, "active"),
            "unit_label": self._catalog_value(product, "unit_label"),
            "tax_code": self._catalog_value(product, "tax_code"),
            "statement_descriptor": self._catalog_value(product, "statement_descriptor"),
            "default_price_id": self._catalog_id(
                self._catalog_value(product, "default_price")
            ),
            "metadata": self._catalog_dict(metadata),
            "created": self._catalog_value(product, "created"),
        }

    def _normalize_price(self, price) -> dict[str, Any]:
        metadata = self._catalog_value(price, "metadata", {})
        recurring_value = self._catalog_value(price, "recurring")
        recurring = None
        if recurring_value is not None:
            recurring = {
                "interval": self._catalog_value(recurring_value, "interval"),
                "interval_count": self._catalog_value(recurring_value, "interval_count"),
                "usage_type": self._catalog_value(recurring_value, "usage_type"),
                "meter_id": self._catalog_id(
                    self._catalog_value(recurring_value, "meter")
                ),
            }
        unit_amount = self._catalog_value(price, "unit_amount")
        return {
            "id": self._catalog_value(price, "id"),
            "product_id": self._catalog_id(self._catalog_value(price, "product")),
            "amount": unit_amount,
            "unit_amount": unit_amount,
            "unit_amount_decimal": self._catalog_value(price, "unit_amount_decimal"),
            "currency": self._catalog_value(price, "currency"),
            "recurring": recurring,
            "lookup_key": self._catalog_value(price, "lookup_key"),
            "nickname": self._catalog_value(price, "nickname"),
            "active": self._catalog_value(price, "active"),
            "tax_behavior": self._catalog_value(price, "tax_behavior"),
            "billing_scheme": self._catalog_value(price, "billing_scheme"),
            "metadata": self._catalog_dict(metadata),
            "created": self._catalog_value(price, "created"),
        }

    # Metered Usage and Billing Meters
    def create_meter(
        self,
        display_name: str,
        event_name: str,
        customer_mapping_key: str = "stripe_customer_id",
        value_settings_key: str = "value",
        default_aggregation_formula: str = "sum",
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Create a Stripe billing meter."""
        params: dict[str, Any] = {
            "display_name": display_name,
            "event_name": event_name,
            "customer_mapping": {
                "type": "by_id",
                "event_payload_key": customer_mapping_key,
            },
            "value_settings": {"event_payload_key": value_settings_key},
            "default_aggregation": {"formula": default_aggregation_formula},
        }
        params.update(extra_params)
        meter = self._client.v1.billing.meters.create(
            params=params,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_meter(meter)

    def get_meter(self, meter_id: str) -> dict[str, Any]:
        """Retrieve a Stripe billing meter."""
        return self._normalize_meter(self._client.v1.billing.meters.retrieve(meter_id))

    def list_meters(self, limit: int = 10, status: str | None = None) -> list[dict[str, Any]]:
        """List Stripe billing meters."""
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        meters = self._client.v1.billing.meters.list(params=params)
        return [self._normalize_meter(meter) for meter in meters.data]

    def list_all_meters(self, status: str | None = None) -> list[dict[str, Any]]:
        """List the complete Stripe billing-meter catalog."""
        params: dict[str, Any] = {"limit": 100}
        if status:
            params["status"] = status
        meters = self._client.v1.billing.meters.list(params=params)
        return [self._normalize_meter(meter) for meter in self._auto_paging_items(meters)]

    def update_meter(
        self,
        meter_id: str,
        display_name: str | None = None,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Update a Stripe billing meter."""
        params = {"display_name": display_name} if display_name is not None else {}
        params.update(extra_params)
        meter = self._client.v1.billing.meters.update(
            meter_id,
            params=params,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_meter(meter)

    def deactivate_meter(self, meter_id: str, idempotency_key: str | None = None) -> dict[str, Any]:
        """Deactivate a Stripe billing meter."""
        meter = self._client.v1.billing.meters.deactivate(
            meter_id,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_meter(meter)

    def reactivate_meter(self, meter_id: str, idempotency_key: str | None = None) -> dict[str, Any]:
        """Reactivate a Stripe billing meter."""
        meter = self._client.v1.billing.meters.reactivate(
            meter_id,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_meter(meter)

    def create_meter_event(
        self,
        event_name: str,
        customer_id: str | None = None,
        value: Decimal | int | str | None = None,
        identifier: str | None = None,
        timestamp: int | None = None,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        **dimensions: Any,
    ) -> dict[str, Any]:
        """Record usage with Stripe Billing Meter Events."""
        event_payload = dict(payload or {})
        if customer_id is not None:
            event_payload.setdefault("stripe_customer_id", customer_id)
        if value is not None:
            event_payload.setdefault("value", str(value))
        event_payload.update({key: value for key, value in dimensions.items() if value is not None})

        if "stripe_customer_id" not in event_payload or "value" not in event_payload:
            raise PaymentValidationError("Meter events require a customer id and usage value")

        params: dict[str, Any] = {"event_name": event_name, "payload": event_payload}
        if identifier:
            params["identifier"] = identifier
        if timestamp is not None:
            params["timestamp"] = timestamp

        meter_event = self._client.v1.billing.meter_events.create(
            params=params,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_meter_event(meter_event)

    def record_usage(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Alias for create_meter_event for application-facing usage recording."""
        return self.create_meter_event(*args, **kwargs)

    def create_meter_event_session(self) -> dict[str, Any]:
        """Create a short-lived session for high-throughput meter event streams."""
        session = self._client.v2.billing.meter_event_session.create()
        return {
            "authentication_token": session.authentication_token,
            "expires_at": session.expires_at,
        }

    def create_meter_event_stream(
        self,
        events: list[dict[str, Any]],
        authentication_token: str | None = None,
    ) -> dict[str, Any]:
        """Send high-throughput meter events through Stripe API v2."""
        client = stripe.StripeClient(authentication_token) if authentication_token else self._client
        client.v2.billing.meter_event_stream.create(params={"events": events})
        return {"submitted": True, "event_count": len(events)}

    def _normalize_meter(self, meter) -> dict[str, Any]:
        aggregation = self._catalog_value(meter, "default_aggregation")
        customer_mapping = self._catalog_value(meter, "customer_mapping")
        value_settings = self._catalog_value(meter, "value_settings")
        return {
            "id": self._catalog_value(meter, "id"),
            "display_name": self._catalog_value(meter, "display_name"),
            "event_name": self._catalog_value(meter, "event_name"),
            "status": self._catalog_value(meter, "status"),
            "aggregation": self._catalog_value(aggregation, "formula"),
            "customer_key": self._catalog_value(customer_mapping, "event_payload_key"),
            "value_key": self._catalog_value(value_settings, "event_payload_key"),
            "created": self._catalog_value(meter, "created"),
        }

    def _normalize_meter_event(self, meter_event) -> dict[str, Any]:
        return {
            "object": getattr(meter_event, "object", "billing.meter_event"),
            "event_name": meter_event.event_name,
            "identifier": getattr(meter_event, "identifier", None),
            "payload": getattr(meter_event, "payload", {}),
            "timestamp": getattr(meter_event, "timestamp", None),
            "created": getattr(meter_event, "created", None),
            "livemode": getattr(meter_event, "livemode", None),
        }

    # Catalog Administration and Stripe Entitlements
    def create_entitlement_feature(
        self,
        *,
        name: str,
        lookup_key: str,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"name": name, "lookup_key": lookup_key}
        if metadata is not None:
            params["metadata"] = metadata
        feature = self._client.v1.entitlements.features.create(
            params=params,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_entitlement_feature(feature)

    def update_entitlement_feature(
        self,
        feature_id: str,
        *,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        active: bool | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        params = {
            key: value
            for key, value in {"name": name, "metadata": metadata, "active": active}.items()
            if value is not None
        }
        feature = self._client.v1.entitlements.features.update(
            feature_id,
            params=params,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_entitlement_feature(feature)

    def list_all_entitlement_features(
        self, *, archived: bool | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": 100}
        if archived is not None:
            params["archived"] = archived
        features = self._client.v1.entitlements.features.list(params=params)
        return [
            self._normalize_entitlement_feature(feature)
            for feature in self._auto_paging_items(features)
        ]

    def attach_entitlement_feature(
        self,
        product_id: str,
        feature_id: str,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        attachment = self._client.v1.products.features.create(
            product_id,
            params={"entitlement_feature": feature_id},
            options=self._request_options(idempotency_key),
        )
        return self._normalize_product_feature(attachment, product_id)

    def detach_entitlement_feature(
        self,
        product_id: str,
        attachment_id: str,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        attachment = self._client.v1.products.features.delete(
            product_id,
            attachment_id,
            params=None,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_product_feature(attachment, product_id)

    def list_all_product_features(self, product_id: str) -> list[dict[str, Any]]:
        attachments = self._client.v1.products.features.list(
            product_id,
            params={"limit": 100},
        )
        return [
            self._normalize_product_feature(attachment, product_id)
            for attachment in self._auto_paging_items(attachments)
        ]

    def discover_catalog(self) -> dict[str, list[dict[str, Any]]]:
        """Discover provider catalog state without reading customers or transactions."""
        meters = self.list_all_meters()
        products = self.list_all_products()
        prices = self.list_all_prices()
        features = self.list_all_entitlement_features()
        product_features = [
            attachment
            for product in products
            for attachment in self.list_all_product_features(product["id"])
        ]

        meter_events = {
            meter["id"]: meter["event_name"]
            for meter in meters
            if meter.get("id") and meter.get("event_name")
        }
        feature_lookup_keys = {
            feature["id"]: feature["lookup_key"]
            for feature in features
            if feature.get("id") and feature.get("lookup_key")
        }
        for price in prices:
            recurring = price.get("recurring")
            if isinstance(recurring, dict):
                recurring["meter_event"] = meter_events.get(recurring.get("meter_id"))
        for attachment in product_features:
            attachment["feature_lookup_key"] = feature_lookup_keys.get(
                attachment.get("feature_id")
            )

        return {
            "meters": sorted(meters, key=lambda item: str(item.get("id") or "")),
            "features": sorted(features, key=lambda item: str(item.get("id") or "")),
            "products": sorted(products, key=lambda item: str(item.get("id") or "")),
            "product_features": sorted(
                product_features,
                key=lambda item: (
                    str(item.get("product_id") or ""),
                    str(item.get("id") or ""),
                ),
            ),
            "prices": sorted(prices, key=lambda item: str(item.get("id") or "")),
        }

    def _normalize_entitlement_feature(self, feature: Any) -> dict[str, Any]:
        metadata = self._catalog_value(feature, "metadata", {})
        return {
            "id": self._catalog_value(feature, "id"),
            "name": self._catalog_value(feature, "name"),
            "lookup_key": self._catalog_value(feature, "lookup_key"),
            "active": self._catalog_value(feature, "active"),
            "metadata": self._catalog_dict(metadata),
        }

    def _normalize_product_feature(
        self, attachment: Any, product_id: str
    ) -> dict[str, Any]:
        entitlement_feature = self._catalog_value(attachment, "entitlement_feature")
        return {
            "id": self._catalog_value(attachment, "id"),
            "product_id": product_id,
            "feature_id": self._catalog_id(entitlement_feature),
        }

    # Billing Portal, Refunds, Discounts, Tax, and Invoice Actions
    def create_billing_portal_session(
        self,
        customer_id: str,
        return_url: str | None = None,
        configuration: str | None = None,
        flow_data: dict[str, Any] | None = None,
        on_behalf_of: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a Stripe-hosted customer billing portal session."""
        params = {
            key: value
            for key, value in {
                "customer": customer_id,
                "return_url": return_url,
                "configuration": configuration,
                "flow_data": flow_data,
                "on_behalf_of": on_behalf_of,
            }.items()
            if value is not None
        }
        session = self._client.v1.billing_portal.sessions.create(
            params=params,
            options=self._request_options(idempotency_key),
        )
        return {"id": session.id, "url": session.url, "customer_id": session.customer}

    def create_refund(
        self,
        payment_intent_id: str | None = None,
        charge_id: str | None = None,
        amount: Decimal | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Create a refund for a PaymentIntent or charge."""
        params = {
            key: value
            for key, value in {
                "payment_intent": payment_intent_id,
                "charge": charge_id,
                "amount": int(amount) if amount is not None else None,
                "reason": reason,
                "metadata": metadata,
            }.items()
            if value is not None
        }
        params.update(extra_params)
        refund = self._client.v1.refunds.create(
            params=params,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_refund(refund)

    def get_refund(self, refund_id: str) -> dict[str, Any]:
        """Retrieve a refund."""
        return self._normalize_refund(self._client.v1.refunds.retrieve(refund_id))

    def list_refunds(
        self,
        payment_intent_id: str | None = None,
        charge_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List refunds."""
        params = {"limit": limit}
        if payment_intent_id:
            params["payment_intent"] = payment_intent_id
        if charge_id:
            params["charge"] = charge_id
        refunds = self._client.v1.refunds.list(params=params)
        return [self._normalize_refund(refund) for refund in refunds.data]

    def create_coupon(
        self,
        percent_off: Decimal | None = None,
        amount_off: Decimal | None = None,
        currency: str | None = None,
        duration: str = "once",
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Create a Stripe coupon."""
        params = {
            key: value
            for key, value in {
                "percent_off": float(percent_off) if percent_off is not None else None,
                "amount_off": int(amount_off) if amount_off is not None else None,
                "currency": currency,
                "duration": duration,
                "name": name,
                "metadata": metadata,
            }.items()
            if value is not None
        }
        params.update(extra_params)
        coupon = self._client.v1.coupons.create(
            params=params,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_coupon(coupon)

    def get_coupon(self, coupon_id: str) -> dict[str, Any]:
        """Retrieve a coupon."""
        return self._normalize_coupon(self._client.v1.coupons.retrieve(coupon_id))

    def delete_coupon(self, coupon_id: str) -> dict[str, Any]:
        """Delete a coupon."""
        result = self._client.v1.coupons.delete(coupon_id)
        return {"id": result.id, "deleted": result.deleted}

    def create_promotion_code(
        self,
        coupon_id: str,
        code: str | None = None,
        customer_id: str | None = None,
        active: bool | None = None,
        metadata: dict[str, Any] | None = None,
        restrictions: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Create a Stripe promotion code for a coupon."""
        params = {
            key: value
            for key, value in {
                "coupon": coupon_id,
                "code": code,
                "customer": customer_id,
                "active": active,
                "metadata": metadata,
                "restrictions": restrictions,
            }.items()
            if value is not None
        }
        params.update(extra_params)
        promotion_code = self._client.v1.promotion_codes.create(
            params=params,
            options=self._request_options(idempotency_key),
        )
        return {
            "id": promotion_code.id,
            "code": promotion_code.code,
            "coupon_id": promotion_code.coupon.id
            if hasattr(promotion_code.coupon, "id")
            else promotion_code.coupon,
            "active": promotion_code.active,
            "metadata": getattr(promotion_code, "metadata", {}),
        }

    def create_tax_rate(
        self,
        display_name: str,
        percentage: Decimal,
        inclusive: bool = False,
        country: str | None = None,
        description: str | None = None,
        jurisdiction: str | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Create a Stripe tax rate."""
        params = {
            key: value
            for key, value in {
                "display_name": display_name,
                "percentage": float(percentage),
                "inclusive": inclusive,
                "country": country,
                "description": description,
                "jurisdiction": jurisdiction,
                "metadata": metadata,
            }.items()
            if value is not None
        }
        tax_rate = self._client.v1.tax_rates.create(
            params=params,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_tax_rate(tax_rate)

    def list_tax_rates(self, active: bool | None = None, limit: int = 10) -> list[dict[str, Any]]:
        """List Stripe tax rates."""
        params: dict[str, Any] = {"limit": limit}
        if active is not None:
            params["active"] = active
        tax_rates = self._client.v1.tax_rates.list(params=params)
        return [self._normalize_tax_rate(tax_rate) for tax_rate in tax_rates.data]

    def create_invoice(
        self,
        customer_id: str,
        auto_advance: bool | None = None,
        collection_method: str | None = None,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """Create an invoice."""
        params = {
            key: value
            for key, value in {
                "customer": customer_id,
                "auto_advance": auto_advance,
                "collection_method": collection_method,
                "metadata": metadata,
            }.items()
            if value is not None
        }
        params.update(extra_params)
        invoice = self._client.v1.invoices.create(
            params=params,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_invoice(invoice)

    def finalize_invoice(
        self, invoice_id: str, idempotency_key: str | None = None
    ) -> dict[str, Any]:
        """Finalize a draft invoice."""
        invoice = self._client.v1.invoices.finalize_invoice(
            invoice_id,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_invoice(invoice)

    def pay_invoice(self, invoice_id: str, idempotency_key: str | None = None) -> dict[str, Any]:
        """Pay an invoice."""
        invoice = self._client.v1.invoices.pay(
            invoice_id,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_invoice(invoice)

    def void_invoice(self, invoice_id: str, idempotency_key: str | None = None) -> dict[str, Any]:
        """Void an invoice."""
        invoice = self._client.v1.invoices.void_invoice(
            invoice_id,
            options=self._request_options(idempotency_key),
        )
        return self._normalize_invoice(invoice)

    def _normalize_invoice(self, invoice) -> dict[str, Any]:
        return {
            "id": invoice.id,
            "customer_id": invoice.customer,
            "amount_due": invoice.amount_due,
            "amount_paid": invoice.amount_paid,
            "status": invoice.status,
            "created": invoice.created,
            "currency": invoice.currency,
            "hosted_invoice_url": getattr(invoice, "hosted_invoice_url", None),
            "invoice_pdf": getattr(invoice, "invoice_pdf", None),
        }

    def _normalize_refund(self, refund) -> dict[str, Any]:
        return {
            "id": refund.id,
            "amount": refund.amount,
            "currency": refund.currency,
            "payment_intent_id": getattr(refund, "payment_intent", None),
            "charge_id": getattr(refund, "charge", None),
            "status": refund.status,
            "reason": getattr(refund, "reason", None),
            "metadata": getattr(refund, "metadata", {}),
        }

    def _normalize_coupon(self, coupon) -> dict[str, Any]:
        return {
            "id": coupon.id,
            "name": getattr(coupon, "name", None),
            "percent_off": getattr(coupon, "percent_off", None),
            "amount_off": getattr(coupon, "amount_off", None),
            "currency": getattr(coupon, "currency", None),
            "duration": coupon.duration,
            "valid": getattr(coupon, "valid", None),
            "metadata": getattr(coupon, "metadata", {}),
        }

    def _normalize_tax_rate(self, tax_rate) -> dict[str, Any]:
        return {
            "id": tax_rate.id,
            "display_name": tax_rate.display_name,
            "percentage": tax_rate.percentage,
            "inclusive": tax_rate.inclusive,
            "active": tax_rate.active,
            "country": getattr(tax_rate, "country", None),
            "metadata": getattr(tax_rate, "metadata", {}),
        }

    # Webhooks
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        webhook_secret: str | None = None,
        thin: bool = False,
    ) -> dict[str, Any]:
        """Verify and parse a Stripe webhook payload."""
        secret = webhook_secret or self.webhook_secret
        if not secret:
            raise ValueError("Stripe webhook secret is required")

        try:
            event = (
                self._client.parse_event_notification(payload, signature, secret)
                if thin
                else self._client.construct_event(payload, signature, secret)
            )
            event_data = getattr(event, "data", None)
            if hasattr(event_data, "object"):
                event_data = event_data.object
            return {
                "type": event.type,
                "data": event_data,
                "id": event.id,
                "object": event,
                "thin": thin,
            }
        except ValueError as e:
            raise ValueError(f"Invalid payload: {e}")
        except stripe.SignatureVerificationError as e:
            raise ValueError(f"Invalid signature: {e}")

    def dispatch_webhook_event(
        self,
        event: dict[str, Any],
        handlers: dict[str, Any],
        processed_event_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        """Dispatch a verified event to a handler with optional id dedupe."""
        event_id = event.get("id")
        if processed_event_ids is not None and event_id in processed_event_ids:
            return {"handled": False, "duplicate": True, "event_id": event_id}

        handler = handlers.get(event.get("type")) or handlers.get("*")
        if handler is None:
            return {"handled": False, "duplicate": False, "event_id": event_id}

        result = handler(event)
        if processed_event_ids is not None and event_id:
            processed_event_ids.add(event_id)
        return {
            "handled": True,
            "duplicate": False,
            "event_id": event_id,
            "result": result,
        }
