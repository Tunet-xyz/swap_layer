"""Stripe webhook events reach handlers as plain data, as PayPal and Square events do."""

import hashlib
import hmac
import json
import time

import pytest

stripe = pytest.importorskip("stripe")

from swap_layer.billing.providers.stripe import StripePaymentProvider  # noqa: E402

SECRET = "whsec_test_webhook_events"

PAYLOAD = json.dumps(
    {
        "id": "evt_1",
        "object": "event",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_1",
                "object": "checkout.session",
                "customer": "cus_1",
                "subscription": "sub_1",
                "metadata": {"platform": "provider", "organization_uuid": "org-1"},
                "line_items": {
                    "object": "list",
                    "data": [{"id": "li_1", "object": "item", "price": {"id": "price_1", "object": "price"}}],
                },
            }
        },
    }
).encode("utf-8")


def stripe_signature(secret: str = SECRET, payload: bytes = PAYLOAD) -> str:
    timestamp = int(time.time())
    signed = f"{timestamp}.".encode() + payload
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def make_provider(webhook_secret: str | None = SECRET) -> StripePaymentProvider:
    return StripePaymentProvider(secret_key="sk_test_webhook_events", webhook_secret=webhook_secret)


def assert_plain(value):
    """Every container in the value is a built-in dict or list."""
    if isinstance(value, dict):
        assert type(value) is dict
        for item in value.values():
            assert_plain(item)
    elif isinstance(value, list):
        assert type(value) is list
        for item in value:
            assert_plain(item)
    else:
        assert not isinstance(value, stripe.StripeObject)


def test_verified_event_data_is_plain_and_supports_get():
    event = make_provider().verify_webhook_signature(PAYLOAD, stripe_signature())

    assert event["type"] == "checkout.session.completed"
    assert event["id"] == "evt_1"
    assert event["thin"] is False
    data = event["data"]
    assert_plain(data)
    assert data.get("id") == "cs_1"
    assert data.get("metadata") == {"platform": "provider", "organization_uuid": "org-1"}
    assert data["line_items"]["data"][0]["price"]["id"] == "price_1"
    # The vendor's Event object stays available for Stripe-specific needs.
    assert isinstance(event["object"], stripe.Event)
    assert event["object"].data.object.id == "cs_1"


def test_dispatched_handlers_can_read_the_data_like_a_dict():
    provider = make_provider()
    event = provider.verify_webhook_signature(PAYLOAD, stripe_signature())

    def handle_checkout(received):
        data = received.get("data") or {}
        return (data.get("customer"), (data.get("metadata") or {}).get("organization_uuid"))

    outcome = provider.dispatch_webhook_event(event, {"checkout.session.completed": handle_checkout})

    assert outcome["handled"] is True
    assert outcome["result"] == ("cus_1", "org-1")


def test_event_without_an_object_keeps_its_data():
    payload = json.dumps({"id": "evt_2", "object": "event", "type": "ping", "data": {}}).encode("utf-8")

    event = make_provider().verify_webhook_signature(payload, stripe_signature(payload=payload))

    assert event["id"] == "evt_2"
    assert_plain(event["data"])


@pytest.mark.parametrize("secret", [None, ""])
def test_missing_webhook_secret_is_refused(secret):
    with pytest.raises(ValueError, match="webhook secret is required"):
        make_provider(webhook_secret=secret).verify_webhook_signature(PAYLOAD, stripe_signature())


def test_signature_from_another_secret_is_refused():
    with pytest.raises(ValueError, match="Invalid signature"):
        make_provider().verify_webhook_signature(PAYLOAD, stripe_signature("whsec_other"))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ({"id": "x"}, {"id": "x"}),
        (stripe.StripeObject.construct_from({"id": "x", "nested": {"a": 1}}, "sk_test"), {"id": "x", "nested": {"a": 1}}),
    ],
)
def test_webhook_data_conversion(value, expected):
    converted = StripePaymentProvider._webhook_data(value)

    assert converted == expected
    assert_plain(converted)
