import base64
import hashlib
import hmac
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from swap_layer.billing.adapter import PaymentValidationError
from swap_layer.billing.providers.square import SquarePaymentProvider
from swap_layer.settings import SwapLayerSettings


class DummyResponse:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload or {}
        self.status_code = status_code
        self.content = b"{}" if payload is not None else b""
        self.text = str(self.payload)

    def json(self):
        return self.payload


def make_provider():
    return SquarePaymentProvider(
        access_token="square-token",
        location_id="LOC-123",
        webhook_signature_key="signature-key",
        webhook_notification_url="https://app.example.com/square/webhook",
    )


def test_create_payment_intent_creates_square_payment():
    provider = make_provider()
    provider.session.request = Mock(
        return_value=DummyResponse(
            {
                "payment": {
                    "id": "PAY-123",
                    "status": "COMPLETED",
                    "amount_money": {"amount": 1234, "currency": "USD"},
                    "receipt_url": "https://square.test/receipt",
                }
            },
            status_code=200,
        )
    )

    payment = provider.create_payment_intent(
        amount=Decimal("1234"),
        currency="usd",
        customer_id="CUS-123",
        payment_method_id="cnon:card-nonce-ok",
        idempotency_key="idem-1",
        metadata={"reference_id": "order-1"},
    )

    assert payment == {
        "id": "PAY-123",
        "amount": 1234,
        "currency": "USD",
        "status": "completed",
        "client_secret": None,
        "metadata": {"receipt_url": "https://square.test/receipt"},
    }
    _, url = provider.session.request.call_args.args[:2]
    assert url.endswith("/v2/payments")
    kwargs = provider.session.request.call_args.kwargs
    assert kwargs["headers"]["Square-Version"] == "2026-05-20"
    assert kwargs["json"]["source_id"] == "cnon:card-nonce-ok"
    assert kwargs["json"]["amount_money"] == {"amount": 1234, "currency": "USD"}
    assert kwargs["json"]["location_id"] == "LOC-123"


def test_create_product_and_price_use_square_catalog_objects():
    provider = make_provider()
    provider.session.request = Mock(
        side_effect=[
            DummyResponse(
                {
                    "catalog_object": {
                        "id": "ITEM-123",
                        "type": "ITEM",
                        "item_data": {"name": "Pro", "description": "Pro plan"},
                    }
                },
                status_code=200,
            ),
            DummyResponse(
                {
                    "catalog_object": {
                        "id": "VAR-123",
                        "type": "ITEM_VARIATION",
                        "item_variation_data": {
                            "item_id": "ITEM-123",
                            "name": "Pro monthly",
                            "price_money": {"amount": 2500, "currency": "GBP"},
                        },
                    }
                },
                status_code=200,
            ),
        ]
    )

    product = provider.create_product("Pro", description="Pro plan", idempotency_key="prod-1")
    price = provider.create_price(
        product_id=product["id"],
        amount=Decimal("2500"),
        currency="gbp",
        nickname="Pro monthly",
        idempotency_key="price-1",
    )

    assert product["id"] == "ITEM-123"
    assert product["active"] is True
    assert price["id"] == "VAR-123"
    assert price["product_id"] == "ITEM-123"
    assert price["amount"] == 2500
    assert price["currency"] == "GBP"
    assert provider.session.request.call_args_list[0].args[1].endswith("/v2/catalog/object")
    assert provider.session.request.call_args_list[1].args[1].endswith("/v2/catalog/object")


def test_create_subscription_posts_to_square_subscriptions():
    provider = make_provider()
    provider.session.request = Mock(
        return_value=DummyResponse(
            {
                "subscription": {
                    "id": "SUB-123",
                    "customer_id": "CUS-123",
                    "plan_variation_id": "PLANVAR-123",
                    "status": "ACTIVE",
                    "start_date": "2026-06-10",
                }
            },
            status_code=200,
        )
    )

    subscription = provider.create_subscription(
        customer_id="CUS-123",
        price_id="PLANVAR-123",
        idempotency_key="sub-1",
    )

    assert subscription["id"] == "SUB-123"
    assert subscription["status"] == "active"
    assert subscription["items"] == [{"price_id": "PLANVAR-123", "quantity": 1}]
    _, url = provider.session.request.call_args.args[:2]
    assert url.endswith("/v2/subscriptions")
    assert provider.session.request.call_args.kwargs["json"]["location_id"] == "LOC-123"


def test_verify_webhook_signature_checks_hmac():
    provider = make_provider()
    payload = b'{"event_id":"evt-1","type":"payment.created","data":{"id":"PAY-123"}}'
    signed_payload = provider.webhook_notification_url.encode("utf-8") + payload
    signature = base64.b64encode(
        hmac.new(
            provider.webhook_signature_key.encode("utf-8"), signed_payload, hashlib.sha256
        ).digest()
    ).decode("utf-8")

    event = provider.verify_webhook_signature(payload, signature)

    assert event == {
        "type": "payment.created",
        "data": {"id": "PAY-123"},
        "id": "evt-1",
        "object": {"event_id": "evt-1", "type": "payment.created", "data": {"id": "PAY-123"}},
    }


def test_metered_usage_is_explicitly_unsupported():
    provider = make_provider()

    with pytest.raises(PaymentValidationError, match="billing meters"):
        provider.create_meter(display_name="Tokens", event_name="tokens_used")


def test_payment_intent_requires_source_id():
    provider = make_provider()

    with pytest.raises(PaymentValidationError, match="source_id"):
        provider.create_payment_intent(amount=Decimal("100"), currency="usd")


def test_billing_factory_returns_square_from_swaplayer_settings():
    mock_settings = SwapLayerSettings(
        billing={
            "provider": "square",
            "square": {
                "access_token": "square-token",
                "location_id": "LOC-123",
                "webhook_signature_key": "signature-key",
                "webhook_notification_url": "https://app.example.com/square/webhook",
                "sandbox": True,
            },
        }
    )

    with patch("swap_layer.billing.factory.get_swaplayer_settings", return_value=mock_settings):
        from swap_layer.billing.factory import get_payment_provider

        provider = get_payment_provider()

    assert isinstance(provider, SquarePaymentProvider)
    assert provider.access_token == "square-token"
    assert provider.location_id == "LOC-123"
    assert provider.sandbox is True
