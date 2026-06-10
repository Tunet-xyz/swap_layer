from decimal import Decimal
import json
from typing import Any

import requests

from ..adapter import (
    PaymentConnectionError,
    PaymentError,
    PaymentProviderAdapter,
    PaymentValidationError,
    ResourceNotFoundError,
)


class PayPalPaymentProvider(PaymentProviderAdapter):
    """PayPal REST implementation of the payment provider interface."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        webhook_id: str | None = None,
        sandbox: bool = True,
        timeout: int = 30,
    ):
        if not client_id or not client_secret:
            raise ValueError("PayPal client_id and client_secret are required")

        self.client_id = client_id
        self.client_secret = client_secret
        self.webhook_id = webhook_id
        self.sandbox = sandbox
        self.timeout = timeout
        self.base_url = "https://api-m.sandbox.paypal.com" if sandbox else "https://api-m.paypal.com"
        self.session = requests.Session()
        self._access_token: str | None = None

    def get_vendor_client(self) -> Any:
        return self.session

    def _unsupported(self, feature: str) -> None:
        raise PaymentValidationError(f"PayPal provider does not support {feature}")

    def _auth_headers(self) -> dict[str, str]:
        if not self._access_token:
            response = self.session.post(
                f"{self.base_url}/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
                timeout=self.timeout,
            )
            self._handle_response(response)
            self._access_token = response.json()["access_token"]
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = self._auth_headers()
        if idempotency_key:
            headers["PayPal-Request-Id"] = idempotency_key
        response = self.session.request(
            method,
            f"{self.base_url}{path}",
            json=json,
            headers=headers,
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
            message = payload.get("message") or payload.get("name") or response.text
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
    def _money(amount: Decimal | int | str, currency: str) -> dict[str, str]:
        value = str(amount) if isinstance(amount, str) else str(Decimal(str(amount)) / Decimal("100"))
        return {"currency_code": currency.upper(), "value": value}

    @staticmethod
    def _amount_from_money(money: dict[str, Any]) -> int | None:
        value = money.get("value")
        if value is None:
            return None
        return int(Decimal(str(value)) * Decimal("100"))

    @staticmethod
    def _find_approval_url(payload: dict[str, Any]) -> str | None:
        for link in payload.get("links", []):
            if link.get("rel") in {"approve", "payer-action"}:
                return link.get("href")
        return None

    # Customer Management
    def create_customer(
        self, email: str, name: str | None = None, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return {
            "id": f"paypal:{email}",
            "email": email,
            "name": name,
            "created": None,
            "metadata": metadata or {},
        }

    def get_customer(self, customer_id: str) -> dict[str, Any]:
        if customer_id.startswith("paypal:"):
            return {"id": customer_id, "email": customer_id.split(":", 1)[1], "name": None, "metadata": {}}
        self._unsupported("remote customer retrieval")

    def update_customer(
        self,
        customer_id: str,
        email: str | None = None,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {"id": customer_id, "email": email, "name": name, "metadata": metadata or {}}

    def delete_customer(self, customer_id: str) -> dict[str, Any]:
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
        payload = {
            "name": name,
            "description": description or name,
            "type": extra_params.pop("type", "SERVICE"),
            "category": extra_params.pop("category", "SOFTWARE"),
        }
        payload.update(extra_params)
        product = self._request("POST", "/v1/catalogs/products", json=payload, idempotency_key=idempotency_key)
        return self._normalize_product(product)

    def get_product(self, product_id: str) -> dict[str, Any]:
        return self._normalize_product(self._request("GET", f"/v1/catalogs/products/{product_id}"))

    def update_product(
        self,
        product_id: str,
        name: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
        active: bool | None = None,
        **extra_params: Any,
    ) -> dict[str, Any]:
        patches = []
        if name is not None:
            patches.append({"op": "replace", "path": "/name", "value": name})
        if description is not None:
            patches.append({"op": "replace", "path": "/description", "value": description})
        if not patches:
            return self.get_product(product_id)
        self._request("PATCH", f"/v1/catalogs/products/{product_id}", json=patches)
        return self.get_product(product_id)

    def list_products(self, limit: int = 10, active: bool | None = None) -> list[dict[str, Any]]:
        payload = self._request("GET", f"/v1/catalogs/products?page_size={limit}")
        return [self._normalize_product(product) for product in payload.get("products", [])]

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
        interval = (recurring or {}).get("interval", "month").upper()
        interval_count = (recurring or {}).get("interval_count", 1)
        payload = {
            "product_id": product_id,
            "name": nickname or lookup_key or f"{product_id} plan",
            "status": "ACTIVE",
            "billing_cycles": [
                {
                    "frequency": {"interval_unit": interval, "interval_count": interval_count},
                    "tenure_type": "REGULAR",
                    "sequence": 1,
                    "total_cycles": (recurring or {}).get("total_cycles", 0),
                    "pricing_scheme": {"fixed_price": self._money(amount, currency)},
                }
            ],
            "payment_preferences": {"auto_bill_outstanding": True},
        }
        payload.update(extra_params)
        plan = self._request("POST", "/v1/billing/plans", json=payload, idempotency_key=idempotency_key)
        return self._normalize_price(plan)

    def get_price(self, price_id: str) -> dict[str, Any]:
        return self._normalize_price(self._request("GET", f"/v1/billing/plans/{price_id}"))

    def list_prices(self, product_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        payload = self._request("GET", f"/v1/billing/plans?page_size={limit}")
        plans = payload.get("plans", [])
        if product_id:
            plans = [plan for plan in plans if plan.get("product_id") == product_id]
        return [self._normalize_price(plan) for plan in plans]

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
        plan_id = price_id or (items or [{}])[0].get("price")
        if not plan_id:
            raise PaymentValidationError("PayPal subscriptions require a plan id as price_id")
        payload = {"plan_id": plan_id}
        if customer_id and not customer_id.startswith("paypal:"):
            payload["subscriber"] = {"payer_id": customer_id}
        elif customer_id.startswith("paypal:"):
            payload["subscriber"] = {"email_address": customer_id.split(":", 1)[1]}
        if metadata:
            payload["custom_id"] = metadata.get("custom_id") or metadata.get("id")
        payload.update(extra_params)
        subscription = self._request("POST", "/v1/billing/subscriptions", json=payload, idempotency_key=idempotency_key)
        return self._normalize_subscription(subscription)

    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        return self._normalize_subscription(self._request("GET", f"/v1/billing/subscriptions/{subscription_id}"))

    def update_subscription(self, subscription_id: str, price_id: str | None = None, metadata: dict[str, Any] | None = None, **extra_params: Any) -> dict[str, Any]:
        patches = []
        if price_id:
            patches.append({"op": "replace", "path": "/plan_id", "value": price_id})
        if metadata and (metadata.get("custom_id") or metadata.get("id")):
            patches.append({"op": "replace", "path": "/custom_id", "value": metadata.get("custom_id") or metadata.get("id")})
        if patches:
            self._request("PATCH", f"/v1/billing/subscriptions/{subscription_id}", json=patches)
        return self.get_subscription(subscription_id)

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> dict[str, Any]:
        self._request("POST", f"/v1/billing/subscriptions/{subscription_id}/cancel", json={"reason": "Cancelled"})
        return {"id": subscription_id, "status": "cancelled", "cancel_at_period_end": at_period_end}

    def pause_subscription(self, subscription_id: str, behavior: str = "void", resumes_at: int | None = None) -> dict[str, Any]:
        self._request("POST", f"/v1/billing/subscriptions/{subscription_id}/suspend", json={"reason": "Paused"})
        return {"id": subscription_id, "status": "suspended"}

    def resume_subscription(self, subscription_id: str, billing_cycle_anchor: str | None = None, proration_behavior: str | None = None) -> dict[str, Any]:
        self._request("POST", f"/v1/billing/subscriptions/{subscription_id}/activate", json={"reason": "Resumed"})
        return {"id": subscription_id, "status": "active"}

    def list_subscriptions(self, customer_id: str, status: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        self._unsupported("listing subscriptions by customer")

    # Payment Methods
    def attach_payment_method(self, customer_id: str, payment_method_id: str) -> dict[str, Any]:
        self._unsupported("attaching payment methods")

    def detach_payment_method(self, payment_method_id: str) -> dict[str, Any]:
        self._unsupported("detaching payment methods")

    def list_payment_methods(self, customer_id: str, method_type: str | None = None) -> list[dict[str, Any]]:
        self._unsupported("listing payment methods")

    def set_default_payment_method(self, customer_id: str, payment_method_id: str) -> dict[str, Any]:
        self._unsupported("default payment methods")

    # Orders / Payment Intents
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
        payload = {
            "intent": extra_params.pop("intent", "CAPTURE"),
            "purchase_units": [{"amount": self._money(amount, currency)}],
        }
        if metadata:
            payload["purchase_units"][0]["custom_id"] = metadata.get("custom_id") or metadata.get("id")
        payload.update(extra_params)
        order = self._request("POST", "/v2/checkout/orders", json=payload, idempotency_key=idempotency_key)
        return self._normalize_order(order)

    def confirm_payment_intent(self, payment_intent_id: str, payment_method_id: str | None = None) -> dict[str, Any]:
        order = self._request("POST", f"/v2/checkout/orders/{payment_intent_id}/capture", json={})
        return self._normalize_order(order)

    def get_payment_intent(self, payment_intent_id: str) -> dict[str, Any]:
        return self._normalize_order(self._request("GET", f"/v2/checkout/orders/{payment_intent_id}"))

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
                application_context={"return_url": success_url, "cancel_url": cancel_url},
            )
            return {"id": subscription["id"], "url": subscription.get("url"), "customer_id": customer_id, "mode": mode, "payment_status": subscription.get("status")}

        if not line_items and not price_id:
            raise PaymentValidationError("PayPal checkout payment mode requires line_items or price_id")
        amount = extra_params.pop("amount", None)
        currency = extra_params.pop("currency", "USD")
        if amount is None:
            amount = (line_items or [{"amount": 0}])[0].get("amount", 0)
        order = self.create_payment_intent(amount=Decimal(str(amount)), currency=currency, metadata=metadata, idempotency_key=idempotency_key, **extra_params)
        return {"id": order["id"], "url": order.get("url"), "customer_id": customer_id, "mode": mode, "payment_status": order.get("status")}

    def get_checkout_session(self, session_id: str) -> dict[str, Any]:
        order = self.get_payment_intent(session_id)
        return {"id": order["id"], "url": order.get("url"), "customer_id": None, "mode": "payment", "payment_status": order.get("status")}

    # Invoices
    def create_invoice(self, customer_id: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"detail": kwargs.pop("detail", {}), "primary_recipients": kwargs.pop("primary_recipients", [])}
        payload.update(kwargs)
        invoice = self._request("POST", "/v2/invoicing/invoices", json=payload)
        return self._normalize_invoice(invoice)

    def get_invoice(self, invoice_id: str) -> dict[str, Any]:
        return self._normalize_invoice(self._request("GET", f"/v2/invoicing/invoices/{invoice_id}"))

    def list_invoices(self, customer_id: str, limit: int = 10) -> list[dict[str, Any]]:
        payload = self._request("GET", f"/v2/invoicing/invoices?page_size={limit}")
        return [self._normalize_invoice(invoice) for invoice in payload.get("items", [])]

    def finalize_invoice(self, invoice_id: str, **kwargs: Any) -> dict[str, Any]:
        return self.get_invoice(invoice_id)

    def pay_invoice(self, invoice_id: str, **kwargs: Any) -> dict[str, Any]:
        self._request("POST", f"/v2/invoicing/invoices/{invoice_id}/send", json=kwargs or {})
        return self.get_invoice(invoice_id)

    def void_invoice(self, invoice_id: str, **kwargs: Any) -> dict[str, Any]:
        self._request("POST", f"/v2/invoicing/invoices/{invoice_id}/cancel", json=kwargs or {"subject": "Invoice voided"})
        return {"id": invoice_id, "status": "voided"}

    # Refunds / Discounts / Tax
    def create_refund(self, payment_intent_id: str | None = None, charge_id: str | None = None, amount: Decimal | None = None, reason: str | None = None, metadata: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        capture_id = charge_id or payment_intent_id
        if not capture_id:
            raise PaymentValidationError("PayPal refunds require a capture_id via charge_id or payment_intent_id")
        payload = {}
        if amount is not None:
            payload["amount"] = self._money(amount, kwargs.pop("currency", "USD"))
        refund = self._request("POST", f"/v2/payments/captures/{capture_id}/refund", json=payload)
        return self._normalize_refund(refund)

    def get_refund(self, refund_id: str) -> dict[str, Any]:
        return self._normalize_refund(self._request("GET", f"/v2/payments/refunds/{refund_id}"))

    def list_refunds(self, payment_intent_id: str | None = None, charge_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        self._unsupported("listing refunds")

    def create_coupon(self, **kwargs: Any) -> dict[str, Any]:
        self._unsupported("coupons")

    def get_coupon(self, coupon_id: str) -> dict[str, Any]:
        self._unsupported("coupons")

    def delete_coupon(self, coupon_id: str) -> dict[str, Any]:
        self._unsupported("coupons")

    def create_promotion_code(self, coupon_id: str, **kwargs: Any) -> dict[str, Any]:
        self._unsupported("promotion codes")

    def create_tax_rate(self, display_name: str, percentage: Decimal, **kwargs: Any) -> dict[str, Any]:
        self._unsupported("tax rate management")

    def list_tax_rates(self, active: bool | None = None, limit: int = 10) -> list[dict[str, Any]]:
        self._unsupported("tax rate management")

    # Metered usage has no direct PayPal equivalent
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
        return {"id": customer_id, "url": return_url, "customer_id": customer_id}

    # Webhooks
    def verify_webhook_signature(self, payload: bytes, signature: str, webhook_secret: str | None = None, thin: bool = False) -> dict[str, Any]:
        webhook_id = webhook_secret or self.webhook_id
        if not webhook_id:
            raise ValueError("PayPal webhook_id is required for webhook verification")
        transmission_id = signature
        event = json.loads(payload.decode("utf-8")) if isinstance(payload, bytes) else payload
        verification = self._request(
            "POST",
            "/v1/notifications/verify-webhook-signature",
            json={
                "auth_algo": event.get("auth_algo", ""),
                "cert_url": event.get("cert_url", ""),
                "transmission_id": transmission_id,
                "transmission_sig": event.get("transmission_sig", ""),
                "transmission_time": event.get("transmission_time", ""),
                "webhook_id": webhook_id,
                "webhook_event": event,
            },
        )
        if verification.get("verification_status") != "SUCCESS":
            raise ValueError("Invalid PayPal webhook signature")
        return {"type": event.get("event_type"), "data": event.get("resource"), "id": event.get("id"), "object": event}

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
    def _normalize_product(self, product: dict[str, Any]) -> dict[str, Any]:
        return {"id": product.get("id"), "name": product.get("name"), "description": product.get("description"), "active": product.get("status", "ACTIVE") == "ACTIVE", "metadata": {}}

    def _normalize_price(self, plan: dict[str, Any]) -> dict[str, Any]:
        cycle = (plan.get("billing_cycles") or [{}])[0]
        price = ((cycle.get("pricing_scheme") or {}).get("fixed_price") or {})
        return {"id": plan.get("id"), "product_id": plan.get("product_id"), "amount": self._amount_from_money(price), "currency": price.get("currency_code"), "recurring": cycle.get("frequency"), "active": plan.get("status") == "ACTIVE", "metadata": {}}

    def _normalize_subscription(self, subscription: dict[str, Any]) -> dict[str, Any]:
        return {"id": subscription.get("id"), "customer_id": ((subscription.get("subscriber") or {}).get("payer_id") or (subscription.get("subscriber") or {}).get("email_address")), "status": (subscription.get("status") or "").lower(), "current_period_start": None, "current_period_end": None, "cancel_at_period_end": False, "canceled_at": None, "items": [{"price_id": subscription.get("plan_id"), "quantity": 1}], "metadata": {"custom_id": subscription.get("custom_id")} if subscription.get("custom_id") else {}, "url": self._find_approval_url(subscription)}

    def _normalize_order(self, order: dict[str, Any]) -> dict[str, Any]:
        money = ((order.get("purchase_units") or [{}])[0].get("amount") or {})
        return {"id": order.get("id"), "amount": self._amount_from_money(money), "currency": money.get("currency_code"), "status": (order.get("status") or "").lower(), "client_secret": None, "metadata": {}, "url": self._find_approval_url(order)}

    def _normalize_invoice(self, invoice: dict[str, Any]) -> dict[str, Any]:
        money = invoice.get("amount") or invoice.get("due_amount") or {}
        return {"id": invoice.get("id"), "customer_id": None, "amount_due": self._amount_from_money(money), "amount_paid": None, "status": invoice.get("status"), "created": invoice.get("detail", {}).get("invoice_date"), "currency": money.get("currency_code"), "hosted_invoice_url": invoice.get("href"), "invoice_pdf": None}

    def _normalize_refund(self, refund: dict[str, Any]) -> dict[str, Any]:
        amount = refund.get("amount") or {}
        return {"id": refund.get("id"), "amount": self._amount_from_money(amount), "currency": amount.get("currency_code"), "payment_intent_id": refund.get("capture_id"), "charge_id": refund.get("capture_id"), "status": (refund.get("status") or "").lower(), "reason": None, "metadata": {}}
