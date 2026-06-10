from decimal import Decimal
from unittest.mock import MagicMock

from swap_layer.billing.providers.stripe import StripePaymentProvider


def make_provider():
    provider = StripePaymentProvider(secret_key="sk_test_123")
    provider._client = MagicMock()
    return provider


def test_create_product_and_price():
    provider = make_provider()
    product = MagicMock()
    product.id = "prod_123"
    product.name = "Pro"
    product.description = "Pro plan"
    product.active = True
    product.metadata = {"tier": "pro"}
    product.created = 123
    provider._client.v1.products.create.return_value = product

    price = MagicMock()
    price.id = "price_123"
    price.product = "prod_123"
    price.unit_amount = 2500
    price.currency = "usd"
    price.recurring = {"interval": "month"}
    price.lookup_key = "pro_monthly"
    price.nickname = "Pro monthly"
    price.active = True
    price.metadata = {}
    provider._client.v1.prices.create.return_value = price

    assert provider.create_product("Pro", description="Pro plan")["id"] == "prod_123"
    assert provider.create_price(
        "prod_123",
        Decimal("2500"),
        "usd",
        recurring={"interval": "month"},
        lookup_key="pro_monthly",
    )["id"] == "price_123"

    provider._client.v1.products.create.assert_called_once_with(
        params={"name": "Pro", "description": "Pro plan"}, options=None
    )
    provider._client.v1.prices.create.assert_called_once()


def test_create_checkout_session_with_common_app_options():
    provider = make_provider()
    session = MagicMock()
    session.id = "cs_123"
    session.url = "https://checkout.stripe.com/cs_123"
    session.customer = "cus_123"
    session.mode = "subscription"
    session.payment_status = "unpaid"
    session.subscription = "sub_123"
    session.payment_intent = None
    session.metadata = {"tenant": "acme"}
    provider._client.v1.checkout.sessions.create.return_value = session

    result = provider.create_checkout_session(
        customer_id="cus_123",
        price_id="price_123",
        success_url="https://app.test/success",
        cancel_url="https://app.test/cancel",
        allow_promotion_codes=True,
        automatic_tax={"enabled": True},
        subscription_data={"metadata": {"tenant": "acme"}},
        idempotency_key="checkout-123",
    )

    assert result["url"].startswith("https://checkout")
    call = provider._client.v1.checkout.sessions.create.call_args
    assert call.kwargs["params"]["allow_promotion_codes"] is True
    assert call.kwargs["params"]["automatic_tax"] == {"enabled": True}
    assert call.kwargs["options"] == {"idempotency_key": "checkout-123"}


def test_create_meter_and_record_usage():
    provider = make_provider()
    meter = MagicMock()
    meter.id = "mtr_123"
    meter.display_name = "Tokens"
    meter.event_name = "tokens_used"
    meter.status = "active"
    meter.created = 123
    provider._client.v1.billing.meters.create.return_value = meter

    event = MagicMock()
    event.object = "billing.meter_event"
    event.event_name = "tokens_used"
    event.identifier = "evt-usage-1"
    event.payload = {"stripe_customer_id": "cus_123", "value": "42"}
    event.timestamp = 123456
    event.created = 123457
    event.livemode = False
    provider._client.v1.billing.meter_events.create.return_value = event

    assert provider.create_meter("Tokens", "tokens_used")["id"] == "mtr_123"
    result = provider.record_usage(
        "tokens_used",
        customer_id="cus_123",
        value=Decimal("42"),
        identifier="evt-usage-1",
        idempotency_key="usage-1",
    )

    assert result["payload"]["value"] == "42"
    call = provider._client.v1.billing.meter_events.create.call_args
    assert call.kwargs["params"]["payload"] == {
        "stripe_customer_id": "cus_123",
        "value": "42",
    }
    assert call.kwargs["options"] == {"idempotency_key": "usage-1"}


def test_portal_refund_coupon_tax_and_invoice_helpers():
    provider = make_provider()

    portal = MagicMock(id="bps_123", url="https://billing.stripe.com/p/session", customer="cus_123")
    provider._client.v1.billing_portal.sessions.create.return_value = portal
    assert provider.create_billing_portal_session("cus_123")["url"].startswith("https://billing")

    refund = MagicMock(
        id="re_123",
        amount=500,
        currency="usd",
        payment_intent="pi_123",
        charge=None,
        status="succeeded",
        reason="requested_by_customer",
        metadata={},
    )
    provider._client.v1.refunds.create.return_value = refund
    assert provider.create_refund(payment_intent_id="pi_123", amount=Decimal("500"))["id"] == "re_123"

    coupon = MagicMock(
        id="coupon_123",
        name="Launch",
        percent_off=20,
        amount_off=None,
        currency=None,
        duration="once",
        valid=True,
        metadata={},
    )
    provider._client.v1.coupons.create.return_value = coupon
    assert provider.create_coupon(percent_off=Decimal("20"), name="Launch")["percent_off"] == 20

    tax_rate = MagicMock(
        id="txr_123",
        display_name="VAT",
        percentage=20,
        inclusive=False,
        active=True,
        country="GB",
        metadata={},
    )
    provider._client.v1.tax_rates.create.return_value = tax_rate
    assert provider.create_tax_rate("VAT", Decimal("20"), country="GB")["country"] == "GB"

    invoice = MagicMock(
        id="in_123",
        customer="cus_123",
        amount_due=1000,
        amount_paid=0,
        status="draft",
        created=123,
        currency="usd",
        hosted_invoice_url=None,
        invoice_pdf=None,
    )
    provider._client.v1.invoices.create.return_value = invoice
    assert provider.create_invoice("cus_123")["id"] == "in_123"


def test_webhook_dispatch_dedupes_and_calls_handler():
    provider = make_provider()
    processed = set()
    calls = []

    def handle_invoice(event):
        calls.append(event["id"])
        return "ok"

    event = {"id": "evt_123", "type": "invoice.payment_succeeded", "data": {}}
    result = provider.dispatch_webhook_event(
        event, {"invoice.payment_succeeded": handle_invoice}, processed_event_ids=processed
    )
    duplicate = provider.dispatch_webhook_event(
        event, {"invoice.payment_succeeded": handle_invoice}, processed_event_ids=processed
    )

    assert result == {"handled": True, "duplicate": False, "event_id": "evt_123", "result": "ok"}
    assert duplicate == {"handled": False, "duplicate": True, "event_id": "evt_123"}
    assert calls == ["evt_123"]
