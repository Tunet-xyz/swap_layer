"""Subscription normalization against real stripe-python objects.

Since API version 2025-03-31.basil, Stripe reports the billing period on each
subscription item, and the subscription object has no period fields at all.
"""

from unittest.mock import MagicMock

import stripe

from swap_layer.billing.providers.stripe import StripePaymentProvider

KEY = "sk_test_123"


def make_provider():
    provider = StripePaymentProvider(secret_key=KEY)
    provider._client = MagicMock()
    return provider


def item(item_id, price_id, start, end, quantity=1):
    return {
        "id": item_id,
        "object": "subscription_item",
        "price": {"id": price_id, "object": "price"},
        "quantity": quantity,
        "current_period_start": start,
        "current_period_end": end,
    }


def subscription(*items, **fields):
    data = {
        "id": "sub_123",
        "object": "subscription",
        "customer": "cus_123",
        "status": "active",
        "cancel_at_period_end": False,
        "canceled_at": None,
        "metadata": {"tenant": "acme"},
        "items": {"object": "list", "data": list(items)},
    }
    data.update(fields)
    return stripe.Subscription.construct_from(data, KEY)


def test_period_comes_from_the_items_on_current_api_versions():
    provider = make_provider()
    provider._client.v1.subscriptions.retrieve.return_value = subscription(
        item("si_1", "price_1", 1_700_000_000, 1_702_592_000)
    )

    result = provider.get_subscription("sub_123")

    assert result == {
        "id": "sub_123",
        "customer_id": "cus_123",
        "status": "active",
        "current_period_start": 1_700_000_000,
        "current_period_end": 1_702_592_000,
        "cancel_at_period_end": False,
        "canceled_at": None,
        "items": [
            {
                "id": "si_1",
                "price_id": "price_1",
                "quantity": 1,
                "current_period_start": 1_700_000_000,
                "current_period_end": 1_702_592_000,
            }
        ],
        "metadata": {"tenant": "acme"},
    }
    assert type(result["metadata"]) is dict


def test_items_with_different_intervals_report_the_period_ending_first():
    provider = make_provider()
    provider._client.v1.subscriptions.retrieve.return_value = subscription(
        item("si_year", "price_year", 100, 400),
        item("si_month", "price_month", 150, 300),
    )

    result = provider.get_subscription("sub_123")

    assert (result["current_period_start"], result["current_period_end"]) == (150, 300)
    assert [entry["current_period_end"] for entry in result["items"]] == [400, 300]


def test_older_api_versions_keep_the_subscription_period():
    provider = make_provider()
    legacy_item = {
        "id": "si_1",
        "object": "subscription_item",
        "price": {"id": "price_1", "object": "price"},
        "quantity": 2,
    }
    provider._client.v1.subscriptions.retrieve.return_value = subscription(
        legacy_item, current_period_start=10, current_period_end=20
    )

    result = provider.get_subscription("sub_123")

    assert (result["current_period_start"], result["current_period_end"]) == (10, 20)
    assert result["items"][0]["current_period_end"] is None


def test_subscription_without_items_or_period_has_no_period():
    provider = make_provider()
    provider._client.v1.subscriptions.retrieve.return_value = subscription(status="incomplete")

    result = provider.get_subscription("sub_123")

    assert result["current_period_start"] is None
    assert result["current_period_end"] is None
    assert result["items"] == []


def test_create_update_cancel_and_list_return_normalized_subscriptions():
    provider = make_provider()
    created = subscription(item("si_1", "price_1", 100, 200))
    provider._client.v1.subscriptions.create.return_value = created
    provider._client.v1.subscriptions.update.return_value = created
    provider._client.v1.subscriptions.cancel.return_value = subscription(
        item("si_1", "price_1", 100, 200), status="canceled", canceled_at=150
    )
    provider._client.v1.subscriptions.list.return_value = stripe.ListObject.construct_from(
        {"object": "list", "data": [created.to_dict()]}, KEY
    )

    assert provider.create_subscription("cus_123", price_id="price_1")["current_period_end"] == 200
    assert provider.update_subscription("sub_123", metadata={"a": "b"})["current_period_end"] == 200
    assert provider.cancel_subscription("sub_123", at_period_end=True)["current_period_start"] == 100
    cancelled = provider.cancel_subscription("sub_123", at_period_end=False)
    assert (cancelled["status"], cancelled["canceled_at"]) == ("canceled", 150)
    listed = provider.list_subscriptions("cus_123")
    assert [entry["current_period_end"] for entry in listed] == [200]


def test_expanded_customer_and_price_objects_normalize_to_ids():
    provider = make_provider()
    provider._client.v1.subscriptions.retrieve.return_value = subscription(
        item("si_1", "price_1", 100, 200),
        customer={"id": "cus_456", "object": "customer"},
    )

    result = provider.get_subscription("sub_123")

    assert result["customer_id"] == "cus_456"
    assert result["items"][0]["price_id"] == "price_1"
