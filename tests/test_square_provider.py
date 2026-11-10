import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
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


def sign(provider, payload: bytes) -> str:
    signed_payload = provider.webhook_notification_url.encode("utf-8") + payload
    return base64.b64encode(
        hmac.new(
            provider.webhook_signature_key.encode("utf-8"), signed_payload, hashlib.sha256
        ).digest()
    ).decode("utf-8")


def square_event(created_at) -> bytes:
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat(timespec="milliseconds").replace("+00:00", "Z")
    event = {"event_id": "evt-1", "type": "payment.created", "data": {"id": "PAY-123"}}
    if created_at is not None:
        event["created_at"] = created_at
    return json.dumps(event).encode("utf-8")


def test_verify_webhook_signature_checks_hmac():
    provider = make_provider()
    created_at = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    payload = square_event(created_at)

    event = provider.verify_webhook_signature(payload, sign(provider, payload))

    assert event == {
        "type": "payment.created",
        "data": {"id": "PAY-123"},
        "id": "evt-1",
        "object": {
            "event_id": "evt-1",
            "type": "payment.created",
            "data": {"id": "PAY-123"},
            "created_at": created_at,
        },
    }
    with pytest.raises(ValueError, match="Invalid Square webhook signature"):
        provider.verify_webhook_signature(payload, sign(provider, payload + b" "))


@pytest.mark.parametrize(
    "created_at",
    [
        timedelta(hours=26),  # older than Square's 24-hour retry window plus slack
        timedelta(minutes=-10),  # too far in the future
        None,  # missing
        "yesterday",
        "2026-11-09 12:00:00",  # not RFC 3339
        12345,
    ],
)
def test_verify_webhook_signature_rejects_events_outside_the_window(created_at):
    provider = make_provider()
    if isinstance(created_at, timedelta):
        created_at = datetime.now(timezone.utc) - created_at
    payload = square_event(created_at)
    with pytest.raises(ValueError, match="created_at|time window"):
        provider.verify_webhook_signature(payload, sign(provider, payload))


@pytest.mark.parametrize(
    "created_at",
    [
        timedelta(hours=24),  # Square's last retry
        timedelta(minutes=-4),  # small clock skew
    ],
)
def test_verify_webhook_signature_accepts_square_retries(created_at):
    provider = make_provider()
    payload = square_event(datetime.now(timezone.utc) - created_at)
    assert provider.verify_webhook_signature(payload, sign(provider, payload))["id"] == "evt-1"


@pytest.mark.parametrize(
    "created_at", ["2026-11-09T10:15:30Z", "2026-11-09T10:15:30.123456789Z", "2026-11-09T12:15:30+02:00"]
)
def test_verify_webhook_signature_parses_rfc3339(created_at):
    provider = make_provider()
    payload = square_event(created_at)
    with patch("swap_layer.billing.providers.square.datetime") as clock:
        clock.now.return_value = datetime(2026, 11, 9, 11, 0, tzinfo=timezone.utc)
        clock.fromisoformat = datetime.fromisoformat
        assert provider.verify_webhook_signature(payload, sign(provider, payload))["id"] == "evt-1"


def test_webhook_age_check_can_be_disabled():
    provider = SquarePaymentProvider(
        access_token="square-token",
        location_id="LOC-123",
        webhook_signature_key="signature-key",
        webhook_notification_url="https://app.example.com/square/webhook",
        webhook_max_age=None,
    )
    payload = square_event("2020-01-01T00:00:00Z")
    assert provider.verify_webhook_signature(payload, sign(provider, payload))["id"] == "evt-1"


def test_repeated_event_ids_are_not_dispatched_twice():
    provider = make_provider()
    payload = square_event(datetime.now(timezone.utc))
    event = provider.verify_webhook_signature(payload, sign(provider, payload))
    handler = Mock(return_value="handled")
    processed: set[str] = set()
    provider.dispatch_webhook_event(event, {"payment.created": handler}, processed)
    provider.dispatch_webhook_event(event, {"payment.created": handler}, processed)
    handler.assert_called_once()


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


@pytest.mark.parametrize("signature", [None, "", "sïgnature", b"bytes"])
def test_malformed_signatures_are_invalid_not_type_errors(signature):
    provider = make_provider()
    payload = square_event(datetime.now(timezone.utc))
    with pytest.raises(ValueError, match="Invalid Square webhook signature"):
        provider.verify_webhook_signature(payload, signature)
