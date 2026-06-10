from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from decimal import Decimal
from typing import Any

import requests

from ..adapter import (
    PaymentConnectionError,
    PaymentError,
    PaymentProviderAdapter,
    PaymentValidationError,
    ResourceNotFoundError,
)


class SquarePaymentProvider(PaymentProviderAdapter):
    """Square REST implementation of the payment provider interface."""

    def __init__(
        self,
        access_token: str,
        location_id: str,
        webhook_signature_key: str | None = None,
        webhook_notification_url: str | None = None,
        sandbox: bool = True,
        api_version: str = "2026-05-20",
        timeout: int = 30,
    ):
        if not access_token or not location_id:
            raise ValueError("Square access_token and location_id are required")

        self.access_token = access_token
        self.location_id = location_id
        self.webhook_signature_key = webhook_signature_key
        self.webhook_notification_url = webhook_notification_url
        self.sandbox = sandbox
        self.api_version = api_version
        self.timeout = timeout
        self.base_url = "https://connect.squareupsandbox.com" if sandbox else "https://connect.squareup.com"
        self.session = requests.Session()

    def get_vendor_client(self) -> Any:
        return self.session

    def _unsupported(self, feature: str) -> None:
        raise PaymentValidationError(f"Square provider does not support {feature}")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Square-Version": self.api_version,
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            json=json_body,
            params=params,
            headers=self._headers(),
            timeout=self.timeout,
        )
        self._handle_response(response)
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def _handle_response(self, response) -> None:
        if response.status_code < 400:
            return
        try:
            payload = response.json()
            errors = payload.get("errors") or []
            message = errors[0].get("detail") or errors[0].get("code") if errors else response.text
        except ValueError:
            message = response.text

        if response.status_code == 404:
            raise ResourceNotFoundError(message)
        if response.status_code in {400, 401, 403, 422}:
            raise PaymentValidationError(message)
        if response.status_code in {408, 409, 429, 500, 502, 503, 504}:
            raise PaymentConnectionError(message)
        raise PaymentError(message)

    @staticmethod
    def _idempotency_key(idempotency_key: str | None = None) -> str:
        return idempotency_key or str(uuid.uuid4())

    @staticmethod
    def _money(amount: Decimal | int | str, currency: str) -> dict[str, Any]:
        return {"amount": int(Decimal(str(amount))), "currency": currency.upper()}

    @staticmethod
    def _amount_from_money(money: dict[str, Any] | None) -> int | None:
        if not money:
            return None
        return money.get("amount")

    # Customer Management
    def create_customer(
        self, email: str, name: str | None = None, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"email_address": email}
        if name:
            parts = name.split(" ", 1)
            payload["given_name"] = parts[0]
            if len(parts) > 1:
                payload["family_name"] = parts[1]
        if metadata:
            payload["reference_id"] = metadata.get("reference_id") or metadata.get("id")
        customer = self._request("POST", "/v2/customers", json_body=payload).get("customer", {})
        return self._normalize_customer(customer)

    def get_customer(self, customer_id: str) -> dict[str, Any]:
        customer = self._request("GET", f"/v2/customers/{customer_id}").get("customer", {})
        return self._normalize_customer(customer)

    def update_customer(
        self,
        customer_id: str,
        email: str | None = None,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if email is not None:
            payload["email_address"] = email
        if name is not None:
            parts = name.split(" ", 1)
            payload["given_name"] = parts[0]
            payload["family_name"] = parts[1] if len(parts) > 1 else ""
        if metadata:
            payload["reference_id"] = metadata.get("reference_id") or metadata.get("id")
        customer = self._request("PUT", f"/v2/customers/{customer_id}", json_body=payload).get("customer", {})
        return self._normalize_customer(customer)

    def delete_customer(self, customer_id: str) -> dict[str, Any]:
        self._request("DELETE", f"/v2/customers/{customer_id}")
        return {"id": customer_id, "deleted": True}

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
        object_id = extra_params.pop("object_id", f"#item-{uuid.uuid4().hex}")
        catalog_object = {
            "type": "ITEM",
            "id": object_id,
            "item_data": {
                "name": name,
                "description": description or "",
            },
        }
        catalog_object.update(extra_params)
        payload = {
            "idempotency_key": self._idempotency_key(idempotency_key),
            "object": catalog_object,
        }
        item = self._request("POST", "/v2/catalog/object", json_body=payload).get("catalog_object", {})
        return self._normalize_product(item)

    def get_product(self, product_id: str) -> dict[str, Any]:
        item = self._request("GET", f"/v2/catalog/object/{product_id}").get("object", {})
        return self._normalize_product(item)

    def update_product(
        self,
        product_id: str,
        name: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        active: bool | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        existing = self._request("GET", f"/v2/catalog/object/{product_id}").get("object", {})
        item_data = existing.get("item_data", {})
        if name is not None:
            item_data["name"] = name
        if description is not None:
            item_data["description"] = description
        existing["item_data"] = item_data
        existing.update(extra_params)
        payload = {"idempotency_key": self._idempotency_key(), "object": existing}
        item = self._request("POST", "/v2/catalog/object", json_body=payload).get("catalog_object", {})
        return self._normalize_product(item)

    def list_products(self, limit: int = 10, active: bool | None = None) -> list[dict[str, Any]]:
        payload = self._request(
            "POST",
            "/v2/catalog/search",
            json_body={"object_types": ["ITEM"], "limit": limit},
        )
        return [self._normalize_product(item) for item in payload.get("objects", [])]

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
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        variation_id = extra_params.pop("object_id", f"#variation-{uuid.uuid4().hex}")
        catalog_object = {
            "type": "ITEM_VARIATION",
            "id": variation_id,
            "item_variation_data": {
                "item_id": product_id,
                "name": nickname or lookup_key or "Default",
                "pricing_type": "FIXED_PRICING",
                "price_money": self._money(amount, currency),
            },
        }
        catalog_object.update(extra_params)
        payload = {
            "idempotency_key": self._idempotency_key(idempotency_key),
            "object": catalog_object,
        }
        variation = self._request("POST", "/v2/catalog/object", json_body=payload).get("catalog_object", {})
        normalized = self._normalize_price(variation)
        normalized["recurring"] = recurring
        return normalized

    def get_price(self, price_id: str) -> dict[str, Any]:
        variation = self._request("GET", f"/v2/catalog/object/{price_id}").get("object", {})
        return self._normalize_price(variation)

    def list_prices(self, product_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        payload = self._request(
            "POST",
            "/v2/catalog/search",
            json_body={"object_types": ["ITEM_VARIATION"], "limit": limit},
        )
        prices = [self._normalize_price(item) for item in payload.get("objects", [])]
        if product_id:
            prices = [price for price in prices if price.get("product_id") == product_id]
        return prices

    # Subscriptions
    def create_subscription(
        self,
        customer_id: str,
        price_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        trial_period_days: int | None = None,
        items: list[dict[str, Any]] | None = None,
        quantity: int | None = None,
        idempotency_key: str | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        plan_variation_id = extra_params.pop("plan_variation_id", None) or price_id or (items or [{}])[0].get("price")
        if not plan_variation_id:
            raise PaymentValidationError("Square subscriptions require a plan_variation_id or price_id")
        payload = {
            "idempotency_key": self._idempotency_key(idempotency_key),
            "location_id": extra_params.pop("location_id", self.location_id),
            "plan_variation_id": plan_variation_id,
            "customer_id": customer_id,
        }
        if extra_params.get("card_id"):
            payload["card_id"] = extra_params.pop("card_id")
        if metadata:
            payload["source"] = metadata.get("source", "swap_layer")
        payload.update(extra_params)
        subscription = self._request("POST", "/v2/subscriptions", json_body=payload).get("subscription", {})
        return self._normalize_subscription(subscription)

    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        subscription = self._request("GET", f"/v2/subscriptions/{subscription_id}").get("subscription", {})
        return self._normalize_subscription(subscription)

    def update_subscription(
        self,
        subscription_id: str,
        price_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        payload = dict(extra_params)
        if price_id:
            payload["plan_variation_id"] = price_id
        subscription = self._request("PUT", f"/v2/subscriptions/{subscription_id}", json_body=payload).get("subscription", {})
        return self._normalize_subscription(subscription)

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> dict[str, Any]:
        subscription = self._request("POST", f"/v2/subscriptions/{subscription_id}/cancel", json_body={}).get("subscription", {})
        return self._normalize_subscription(subscription) if subscription else {"id": subscription_id, "status": "canceled", "cancel_at_period_end": at_period_end}

    def pause_subscription(self, subscription_id: str, behavior: str = "void", resumes_at: int | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if resumes_at is not None:
            payload["pause_effective_date"] = resumes_at
        subscription = self._request("POST", f"/v2/subscriptions/{subscription_id}/pause", json_body=payload).get("subscription", {})
        return self._normalize_subscription(subscription) if subscription else {"id": subscription_id, "status": "paused"}

    def resume_subscription(self, subscription_id: str, billing_cycle_anchor: str | None = None, proration_behavior: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        subscription = self._request("POST", f"/v2/subscriptions/{subscription_id}/resume", json_body=payload).get("subscription", {})
        return self._normalize_subscription(subscription) if subscription else {"id": subscription_id, "status": "active"}

    def list_subscriptions(self, customer_id: str, status: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"customer_ids": [customer_id]}
        if status:
            query["status"] = status.upper()
        payload = self._request("POST", "/v2/subscriptions/search", json_body={"query": query, "limit": limit})
        return [self._normalize_subscription(item) for item in payload.get("subscriptions", [])]

    # Payment Methods
    def attach_payment_method(self, customer_id: str, payment_method_id: str) -> dict[str, Any]:
        return {"id": payment_method_id, "customer_id": customer_id, "type": "card"}

    def detach_payment_method(self, payment_method_id: str) -> dict[str, Any]:
        self._request("POST", f"/v2/cards/{payment_method_id}/disable", json_body={})
        return {"id": payment_method_id, "customer_id": None}

    def list_payment_methods(self, customer_id: str, method_type: str | None = None) -> list[dict[str, Any]]:
        payload = self._request("GET", "/v2/cards", params={"customer_id": customer_id})
        return [self._normalize_card(card) for card in payload.get("cards", [])]

    def set_default_payment_method(self, customer_id: str, payment_method_id: str) -> dict[str, Any]:
        return {"id": customer_id, "default_payment_method": payment_method_id}

    # Payments / Checkout
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
        source_id = payment_method_id or extra_params.pop("source_id", None)
        if not source_id:
            raise PaymentValidationError("Square payments require a source_id or payment_method_id")
        payload = {
            "idempotency_key": self._idempotency_key(idempotency_key),
            "source_id": source_id,
            "amount_money": self._money(amount, currency),
            "location_id": extra_params.pop("location_id", self.location_id),
            "autocomplete": extra_params.pop("autocomplete", True),
        }
        if customer_id:
            payload["customer_id"] = customer_id
        if metadata:
            payload["reference_id"] = metadata.get("reference_id") or metadata.get("id")
            payload["note"] = metadata.get("note", "")
        payload.update(extra_params)
        payment = self._request("POST", "/v2/payments", json_body=payload).get("payment", {})
        return self._normalize_payment(payment)

    def confirm_payment_intent(self, payment_intent_id: str, payment_method_id: str | None = None) -> dict[str, Any]:
        payment = self._request("POST", f"/v2/payments/{payment_intent_id}/complete", json_body={}).get("payment", {})
        return self._normalize_payment(payment)

    def get_payment_intent(self, payment_intent_id: str) -> dict[str, Any]:
        payment = self._request("GET", f"/v2/payments/{payment_intent_id}").get("payment", {})
        return self._normalize_payment(payment)

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
        if mode == "subscription":
            subscription = self.create_subscription(
                customer_id=customer_id or "",
                price_id=price_id,
                metadata=metadata,
                idempotency_key=idempotency_key,
                **extra_params,
            )
            return {"id": subscription["id"], "url": None, "customer_id": customer_id, "mode": mode, "payment_status": subscription.get("status")}

        order_line_items = line_items or [{"name": extra_params.pop("name", price_id or "Item"), "quantity": str(quantity)}]
        payload = {
            "idempotency_key": self._idempotency_key(idempotency_key),
            "order": {"location_id": self.location_id, "line_items": order_line_items},
            "checkout_options": {},
        }
        if success_url:
            payload["checkout_options"]["redirect_url"] = success_url
        payload.update(extra_params)
        link = self._request("POST", "/v2/online-checkout/payment-links", json_body=payload).get("payment_link", {})
        return {"id": link.get("id"), "url": link.get("url"), "customer_id": customer_id, "mode": mode, "payment_status": None}

    def get_checkout_session(self, session_id: str) -> dict[str, Any]:
        link = self._request("GET", f"/v2/online-checkout/payment-links/{session_id}").get("payment_link", {})
        return {"id": link.get("id"), "url": link.get("url"), "customer_id": None, "mode": "payment", "payment_status": None}

    # Invoices
    def create_invoice(self, customer_id: str, **kwargs: Any) -> dict[str, Any]:
        invoice = {
            "location_id": kwargs.pop("location_id", self.location_id),
            "primary_recipient": {"customer_id": customer_id},
            "payment_requests": kwargs.pop("payment_requests", [{"request_type": "BALANCE", "due_date": kwargs.pop("due_date", None)}]),
        }
        if invoice["payment_requests"][0].get("due_date") is None:
            invoice["payment_requests"][0].pop("due_date")
        invoice.update(kwargs)
        payload = {"idempotency_key": self._idempotency_key(kwargs.pop("idempotency_key", None)), "invoice": invoice}
        square_invoice = self._request("POST", "/v2/invoices", json_body=payload).get("invoice", {})
        return self._normalize_invoice(square_invoice)

    def get_invoice(self, invoice_id: str) -> dict[str, Any]:
        invoice = self._request("GET", f"/v2/invoices/{invoice_id}").get("invoice", {})
        return self._normalize_invoice(invoice)

    def list_invoices(self, customer_id: str, limit: int = 10) -> list[dict[str, Any]]:
        payload = self._request("GET", "/v2/invoices", params={"location_id": self.location_id, "limit": limit})
        invoices = [self._normalize_invoice(invoice) for invoice in payload.get("invoices", [])]
        return [invoice for invoice in invoices if invoice.get("customer_id") in {None, customer_id}]

    def finalize_invoice(self, invoice_id: str, **kwargs: Any) -> dict[str, Any]:
        invoice = self._request("POST", f"/v2/invoices/{invoice_id}/publish", json_body=kwargs or {"version": 0}).get("invoice", {})
        return self._normalize_invoice(invoice)

    def pay_invoice(self, invoice_id: str, **kwargs: Any) -> dict[str, Any]:
        self._unsupported("direct invoice payment")

    def void_invoice(self, invoice_id: str, **kwargs: Any) -> dict[str, Any]:
        invoice = self._request("POST", f"/v2/invoices/{invoice_id}/cancel", json_body=kwargs or {"version": 0}).get("invoice", {})
        return self._normalize_invoice(invoice) if invoice else {"id": invoice_id, "status": "voided"}

    # Refunds / Discounts / Tax / Meters
    def create_refund(self, payment_intent_id: str | None = None, charge_id: str | None = None, amount: Decimal | None = None, reason: str | None = None, metadata: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        payment_id = payment_intent_id or charge_id
        if not payment_id:
            raise PaymentValidationError("Square refunds require a payment_id via payment_intent_id or charge_id")
        if amount is None:
            raise PaymentValidationError("Square refunds require an amount")
        payload = {
            "idempotency_key": self._idempotency_key(kwargs.pop("idempotency_key", None)),
            "payment_id": payment_id,
            "amount_money": self._money(amount, kwargs.pop("currency", "USD")),
        }
        if reason:
            payload["reason"] = reason
        refund = self._request("POST", "/v2/refunds", json_body=payload).get("refund", {})
        return self._normalize_refund(refund)

    def get_refund(self, refund_id: str) -> dict[str, Any]:
        refund = self._request("GET", f"/v2/refunds/{refund_id}").get("refund", {})
        return self._normalize_refund(refund)

    def list_refunds(self, payment_intent_id: str | None = None, charge_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        payload = self._request("GET", "/v2/refunds", params={"limit": limit})
        refunds = [self._normalize_refund(refund) for refund in payload.get("refunds", [])]
        payment_id = payment_intent_id or charge_id
        return [refund for refund in refunds if refund.get("payment_intent_id") == payment_id] if payment_id else refunds

    def create_coupon(self, **kwargs: Any) -> dict[str, Any]:
        self._unsupported("provider-agnostic coupons")

    def get_coupon(self, coupon_id: str) -> dict[str, Any]:
        self._unsupported("provider-agnostic coupons")

    def delete_coupon(self, coupon_id: str) -> dict[str, Any]:
        self._unsupported("provider-agnostic coupons")

    def create_promotion_code(self, coupon_id: str, **kwargs: Any) -> dict[str, Any]:
        self._unsupported("provider-agnostic promotion codes")

    def create_tax_rate(self, display_name: str, percentage: Decimal, **kwargs: Any) -> dict[str, Any]:
        self._unsupported("provider-agnostic tax rate management")

    def list_tax_rates(self, active: bool | None = None, limit: int = 10) -> list[dict[str, Any]]:
        self._unsupported("provider-agnostic tax rate management")

    def create_meter(self, display_name: str, event_name: str, **kwargs: Any) -> dict[str, Any]:
        self._unsupported("billing meters")

    def get_meter(self, meter_id: str) -> dict[str, Any]:
        self._unsupported("billing meters")

    def list_meters(self, limit: int = 10, status: str | None = None) -> list[dict[str, Any]]:
        self._unsupported("billing meters")

    def create_meter_event(self, event_name: str, customer_id: str | None = None, value: Decimal | int | str | None = None, **kwargs: Any) -> dict[str, Any]:
        self._unsupported("meter events")

    def record_usage(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self._unsupported("metered usage")

    def create_meter_event_session(self) -> dict[str, Any]:
        self._unsupported("high-throughput meter event sessions")

    def create_meter_event_stream(self, events: list[dict[str, Any]], authentication_token: str | None = None) -> dict[str, Any]:
        self._unsupported("high-throughput meter event streams")

    def create_billing_portal_session(self, customer_id: str, return_url: str | None = None, **kwargs: Any) -> dict[str, Any]:
        self._unsupported("hosted customer billing portal")

    # Webhooks
    def verify_webhook_signature(self, payload: bytes, signature: str, webhook_secret: str | None = None, thin: bool = False) -> dict[str, Any]:
        signature_key = webhook_secret or self.webhook_signature_key
        notification_url = self.webhook_notification_url
        if not signature_key or not notification_url:
            raise ValueError("Square webhook_signature_key and webhook_notification_url are required")
        raw_body = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        signed_payload = f"{notification_url}{raw_body}".encode("utf-8")
        digest = hmac.new(signature_key.encode("utf-8"), signed_payload, hashlib.sha256).digest()
        expected = base64.b64encode(digest).decode("utf-8")
        if not hmac.compare_digest(expected, signature):
            raise ValueError("Invalid Square webhook signature")
        event = json.loads(raw_body)
        return {"type": event.get("type"), "data": event.get("data"), "id": event.get("event_id"), "object": event}

    def dispatch_webhook_event(self, event: dict[str, Any], handlers: dict[str, Any], processed_event_ids: set[str] | None = None) -> dict[str, Any]:
        event_id = event.get("id")
        if processed_event_ids is not None and event_id in processed_event_ids:
            return {"handled": False, "duplicate": True, "event_id": event_id}
        handler = handlers.get(event.get("type")) or handlers.get("*")
        if handler is None:
            return {"handled": False, "duplicate": False, "event_id": event_id}
        result = handler(event)
        if processed_event_ids is not None and event_id:
            processed_event_ids.add(event_id)
        return {"handled": True, "duplicate": False, "event_id": event_id, "result": result}

    # Normalizers
    def _normalize_customer(self, customer: dict[str, Any]) -> dict[str, Any]:
        name = " ".join(part for part in [customer.get("given_name"), customer.get("family_name")] if part) or None
        return {"id": customer.get("id"), "email": customer.get("email_address"), "name": name, "created": customer.get("created_at"), "metadata": {"reference_id": customer.get("reference_id")} if customer.get("reference_id") else {}}

    def _normalize_product(self, item: dict[str, Any]) -> dict[str, Any]:
        data = item.get("item_data", {})
        return {"id": item.get("id"), "name": data.get("name"), "description": data.get("description"), "active": not item.get("is_deleted", False), "metadata": {}}

    def _normalize_price(self, variation: dict[str, Any]) -> dict[str, Any]:
        data = variation.get("item_variation_data", {})
        money = data.get("price_money") or {}
        return {"id": variation.get("id"), "product_id": data.get("item_id"), "amount": self._amount_from_money(money), "currency": money.get("currency"), "recurring": None, "active": not variation.get("is_deleted", False), "metadata": {}}

    def _normalize_subscription(self, subscription: dict[str, Any]) -> dict[str, Any]:
        return {"id": subscription.get("id"), "customer_id": subscription.get("customer_id"), "status": (subscription.get("status") or "").lower(), "current_period_start": subscription.get("start_date"), "current_period_end": subscription.get("charged_through_date"), "cancel_at_period_end": False, "canceled_at": subscription.get("canceled_date"), "items": [{"price_id": subscription.get("plan_variation_id"), "quantity": 1}], "metadata": {}}

    def _normalize_card(self, card: dict[str, Any]) -> dict[str, Any]:
        return {"id": card.get("id"), "customer_id": card.get("customer_id"), "type": "card", "card": {"brand": card.get("card_brand"), "last4": card.get("last_4"), "exp_month": card.get("exp_month"), "exp_year": card.get("exp_year")}}

    def _normalize_payment(self, payment: dict[str, Any]) -> dict[str, Any]:
        money = payment.get("amount_money") or payment.get("total_money") or {}
        return {"id": payment.get("id"), "amount": self._amount_from_money(money), "currency": money.get("currency"), "status": (payment.get("status") or "").lower(), "client_secret": None, "metadata": {"receipt_url": payment.get("receipt_url")} if payment.get("receipt_url") else {}}

    def _normalize_invoice(self, invoice: dict[str, Any]) -> dict[str, Any]:
        payment_requests = invoice.get("payment_requests") or [{}]
        total = invoice.get("invoice_total_money") or invoice.get("total_money") or {}
        recipient = invoice.get("primary_recipient") or {}
        return {"id": invoice.get("id"), "customer_id": recipient.get("customer_id"), "amount_due": self._amount_from_money(total), "amount_paid": None, "status": (invoice.get("status") or "").lower(), "created": invoice.get("created_at"), "currency": total.get("currency"), "hosted_invoice_url": payment_requests[0].get("computed_amount_money", {}).get("currency"), "invoice_pdf": None}

    def _normalize_refund(self, refund: dict[str, Any]) -> dict[str, Any]:
        money = refund.get("amount_money") or {}
        return {"id": refund.get("id"), "amount": self._amount_from_money(money), "currency": money.get("currency"), "payment_intent_id": refund.get("payment_id"), "charge_id": refund.get("payment_id"), "status": (refund.get("status") or "").lower(), "reason": refund.get("reason"), "metadata": {}}