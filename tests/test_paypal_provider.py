from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from swap_layer.billing.adapter import PaymentValidationError
from swap_layer.billing.providers.paypal import PayPalPaymentProvider
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
    provider = PayPalPaymentProvider(
        client_id="paypal-client",
        client_secret="paypal-secret",
        webhook_id="WH-123",
    )
    provider.session.post = Mock(return_value=DummyResponse({"access_token": "token-123"}))
    return provider


def test_create_payment_intent_creates_paypal_order():
    provider = make_provider()
    provider.session.request = Mock(
        return_value=DummyResponse(
            {
                "id": "ORDER-123",
                "status": "CREATED",
                "purchase_units": [{"amount": {"value": "12.34", "currency_code": "USD"}}],
                "links": [{"rel": "approve", "href": "https://paypal.test/approve"}],
            },
            status_code=201,
        )
    )

    order = provider.create_payment_intent(
        amount=Decimal("1234"),
        currency="usd",
        metadata={"custom_id": "order-1"},
        idempotency_key="idem-1",
    )

    assert order == {
        "id": "ORDER-123",
        "amount": 1234,
        "currency": "USD",
        "status": "created",
        "client_secret": None,
        "metadata": {},
        "url": "https://paypal.test/approve",
    }
    _, url = provider.session.request.call_args.args[:2]
    assert url.endswith("/v2/checkout/orders")
    kwargs = provider.session.request.call_args.kwargs
    assert kwargs["headers"]["PayPal-Request-Id"] == "idem-1"
    assert kwargs["json"]["purchase_units"][0]["amount"] == {
        "currency_code": "USD",
        "value": "12.34",
    }
    assert kwargs["json"]["purchase_units"][0]["custom_id"] == "order-1"


def test_create_product_and_price_use_catalog_products_and_billing_plans():
    provider = make_provider()
    provider.session.request = Mock(
        side_effect=[
            DummyResponse(
                {
                    "id": "PROD-123",
                    "name": "Pro",
                    "description": "Pro plan",
                    "status": "ACTIVE",
                },
                status_code=201,
            ),
            DummyResponse(
                {
                    "id": "P-123",
                    "product_id": "PROD-123",
                    "status": "ACTIVE",
                    "billing_cycles": [
                        {
                            "frequency": {"interval_unit": "MONTH", "interval_count": 1},
                            "pricing_scheme": {
                                "fixed_price": {"value": "25", "currency_code": "GBP"}
                            },
                        }
                    ],
                },
                status_code=201,
            ),
        ]
    )

    product = provider.create_product("Pro", description="Pro plan")
    price = provider.create_price(
        product_id=product["id"],
        amount=Decimal("2500"),
        currency="gbp",
        recurring={"interval": "month"},
        nickname="Pro monthly",
    )

    assert product["id"] == "PROD-123"
    assert product["active"] is True
    assert price["id"] == "P-123"
    assert price["amount"] == 2500
    assert price["currency"] == "GBP"
    first_call = provider.session.request.call_args_list[0]
    second_call = provider.session.request.call_args_list[1]
    assert first_call.args[1].endswith("/v1/catalogs/products")
    assert second_call.args[1].endswith("/v1/billing/plans")


def test_metered_usage_is_explicitly_unsupported():
    provider = make_provider()

    with pytest.raises(PaymentValidationError, match="billing meters"):
        provider.create_meter(display_name="Tokens", event_name="tokens_used")


PAYPAL_EVENT = b"""{
    "id": "WH-EVENT-1",
    "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
    "resource": {"id": "I-SUB-1"}
}"""
PAYPAL_HEADERS = {
    "PAYPAL-AUTH-ALGO": "SHA256withRSA",
    "PAYPAL-CERT-URL": "https://api-m.sandbox.paypal.com/certs/CERT-1",
    "PAYPAL-TRANSMISSION-ID": "transmission-id",
    "PAYPAL-TRANSMISSION-SIG": "transmission-sig",
    "PAYPAL-TRANSMISSION-TIME": "2026-06-10T12:00:00Z",
}


def test_verify_webhook_signature_uses_paypal_verification_api():
    provider = make_provider()
    provider.session.request = Mock(return_value=DummyResponse({"verification_status": "SUCCESS"}))

    event = provider.verify_webhook_signature(PAYPAL_EVENT, signature="", headers=PAYPAL_HEADERS)

    assert event["id"] == "WH-EVENT-1"
    assert event["type"] == "BILLING.SUBSCRIPTION.ACTIVATED"
    assert event["data"] == {"id": "I-SUB-1"}
    verification_payload = provider.session.request.call_args.kwargs["json"]
    assert verification_payload == {
        "auth_algo": "SHA256withRSA",
        "cert_url": "https://api-m.sandbox.paypal.com/certs/CERT-1",
        "transmission_id": "transmission-id",
        "transmission_sig": "transmission-sig",
        "transmission_time": "2026-06-10T12:00:00Z",
        "webhook_id": "WH-123",
        "webhook_event": {
            "id": "WH-EVENT-1",
            "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
            "resource": {"id": "I-SUB-1"},
        },
    }


def test_verify_webhook_signature_reads_django_meta_and_signature_argument():
    provider = make_provider()
    provider.session.request = Mock(return_value=DummyResponse({"verification_status": "SUCCESS"}))
    meta = {
        "HTTP_" + name.replace("-", "_"): value
        for name, value in PAYPAL_HEADERS.items()
        if name != "PAYPAL-TRANSMISSION-SIG"
    }

    provider.verify_webhook_signature(PAYPAL_EVENT, signature="from-argument", headers=meta)

    verification_payload = provider.session.request.call_args.kwargs["json"]
    assert verification_payload["transmission_id"] == "transmission-id"
    assert verification_payload["transmission_sig"] == "from-argument"


def test_verify_webhook_signature_needs_every_transmission_header():
    provider = make_provider()
    provider.session.request = Mock()
    headers = {k: v for k, v in PAYPAL_HEADERS.items() if k != "PAYPAL-CERT-URL"}

    with pytest.raises(ValueError, match="PAYPAL-CERT-URL"):
        provider.verify_webhook_signature(PAYPAL_EVENT, signature="sig", headers=headers)
    with pytest.raises(ValueError, match="PAYPAL-AUTH-ALGO"):
        provider.verify_webhook_signature(PAYPAL_EVENT, signature="sig")
    provider.session.request.assert_not_called()


def test_verify_webhook_signature_rejects_failed_verification():
    provider = make_provider()
    provider.session.request = Mock(return_value=DummyResponse({"verification_status": "FAILURE"}))

    with pytest.raises(ValueError, match="Invalid PayPal webhook signature"):
        provider.verify_webhook_signature(PAYPAL_EVENT, signature="", headers=PAYPAL_HEADERS)


def test_billing_portal_is_explicitly_unsupported():
    with pytest.raises(PaymentValidationError, match="billing portal"):
        make_provider().create_billing_portal_session("paypal:a@example.com", "https://app/")


def test_customer_handles_are_local_only():
    provider = make_provider()
    provider.session.request = Mock()

    created = provider.create_customer("a@example.com", name="A")
    assert created["id"] == "paypal:a@example.com"
    assert created["local_only"] is True
    assert provider.get_customer(created["id"])["email"] == "a@example.com"
    updated = provider.update_customer(created["id"], email="b@example.com")
    assert updated["id"] == "paypal:b@example.com"
    assert provider.delete_customer(updated["id"]) == {
        "id": "paypal:b@example.com",
        "deleted": True,
        "local_only": True,
    }
    for call in (
        lambda: provider.update_customer("PAYER-1", email="c@example.com"),
        lambda: provider.delete_customer("PAYER-1"),
        lambda: provider.get_customer("PAYER-1"),
        lambda: provider.create_customer(""),
    ):
        with pytest.raises(PaymentValidationError):
            call()
    provider.session.request.assert_not_called()


def test_dispatch_webhook_event_deduplicates_events():
    provider = make_provider()
    processed = {"evt_seen"}
    handler = Mock(return_value="ok")

    duplicate = provider.dispatch_webhook_event(
        {"id": "evt_seen", "type": "payment"}, {"payment": handler}, processed
    )
    handled = provider.dispatch_webhook_event(
        {"id": "evt_new", "type": "payment"}, {"payment": handler}, processed
    )

    assert duplicate == {"handled": False, "duplicate": True, "event_id": "evt_seen"}
    assert handled["handled"] is True
    assert handled["result"] == "ok"
    assert "evt_new" in processed


def test_billing_factory_returns_paypal_from_swaplayer_settings():
    mock_settings = SwapLayerSettings(
        billing={
            "provider": "paypal",
            "paypal": {
                "client_id": "paypal-client",
                "client_secret": "paypal-secret",
                "webhook_id": "WH-123",
                "sandbox": True,
            },
        }
    )

    with patch("swap_layer.billing.factory.get_swaplayer_settings", return_value=mock_settings):
        from swap_layer.billing.factory import get_payment_provider

        provider = get_payment_provider()

    assert isinstance(provider, PayPalPaymentProvider)
    assert provider.client_id == "paypal-client"
    assert provider.webhook_id == "WH-123"
    assert provider.sandbox is True


@pytest.mark.parametrize("currency, expected", [("GBP", "12.34"), ("JPY", "1234"), ("HUF", "1234"), ("TWD", "1234")])
def test_currency_minor_units_round_trip(currency, expected):
    money = PayPalPaymentProvider._money(Decimal("1234"), currency)
    assert money == {"currency_code": currency, "value": expected}
    assert PayPalPaymentProvider._amount_from_money(money) == 1234


@pytest.mark.parametrize("amount", [Decimal("12.5"), Decimal("NaN"), Decimal("Infinity")])
def test_invalid_numeric_minor_units_fail_before_request(amount):
    provider = PayPalPaymentProvider("fixture-client", "fixture-secret")
    with patch.object(provider, "_request") as request:
        with pytest.raises(PaymentValidationError):
            provider.create_payment_intent(amount, "GBP")
    request.assert_not_called()


@pytest.mark.parametrize("currency, value", [("GBP", "1.001"), ("JPY", "1.1"), ("HUF", "NaN")])
def test_provider_amounts_are_never_silently_truncated(currency, value):
    with pytest.raises(PaymentValidationError):
        PayPalPaymentProvider._amount_from_money({"currency_code": currency, "value": value})


def test_amount_conversion_preserves_decimal_precision():
    amount = Decimal("100000000000000000000000000001")
    money = PayPalPaymentProvider._money(amount, "GBP")
    assert money["value"] == "1000000000000000000000000000.01"
    assert PayPalPaymentProvider._amount_from_money(money) == int(amount)


def test_verify_webhook_signature_accepts_a_text_payload():
    provider = make_provider()
    provider.session.request = Mock(return_value=DummyResponse({"verification_status": "SUCCESS"}))

    event = provider.verify_webhook_signature(PAYPAL_EVENT.decode("utf-8"), signature="", headers=PAYPAL_HEADERS)

    assert event["id"] == "WH-EVENT-1"
