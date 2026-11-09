# Billing

Use `get_provider("payments")` with `billing.provider` set to `stripe`, `paypal`, or `square`. The modules are under `swap_layer.billing`, including customers, subscriptions, payment intents, products and provider implementations. Changing providers requires application and data review.

## Configure

```python
import os
from swap_layer import configure, get_provider
configure(billing={"provider":"stripe", "stripe":{
    "secret_key": os.environ["STRIPE_SECRET_KEY"],
    "webhook_secret": os.environ.get("STRIPE_WEBHOOK_SECRET"),
}})
payments = get_provider("payments")
```

Install `SwapLayer[stripe]` for Stripe 16.x. PayPal and Square use the core Requests dependency. In Django, use the same structure as `SWAPLAYER` or a `SwapLayerSettings` instance. Legacy `PAYMENT_PROVIDER` and provider key settings remain supported.

PayPal configuration is `billing={'provider':'paypal','paypal':{'client_id':...,'client_secret':...,'webhook_id':...,'sandbox':True}}`. Square uses `billing={'provider':'square','square':{'access_token':...,'location_id':...,'webhook_signature_key':...,'webhook_notification_url':...,'sandbox':True}}`. Read credentials from the caller's environment. A test label does not switch credentials to sandbox mode automatically.

## Capability boundaries

| Surface | Stripe | PayPal / Square |
| --- | --- | --- |
| Customers, payments, products, prices, subscriptions, checkout, invoices, refunds | Provider adapter operations | Provider-specific mappings and limitations |
| Metered billing, promotion codes, tax-rate objects, hosted billing portal | Broad Stripe surface | Unsupported Stripe-specific operations raise validation errors |
| Entitlements and catalog discovery | Stripe-specific extensions | No equivalent common guarantee |
| Webhook verification | Stripe signature and endpoint secret | PayPal verification API; Square signature also needs notification URL |

PayPal `verify_webhook_signature(payload, signature)` uses `signature` as the transmission ID and reads `auth_algo`, `cert_url`, `transmission_sig` and `transmission_time` from the JSON `payload`. It requires a `webhook_id` (configured, or passed as `webhook_secret`) and fails closed: any verification status other than `SUCCESS` raises.

Normalized objects include provider IDs and status fields; IDs cannot be moved between accounts/vendors by changing configuration. Some provider-specific invoice/customer operations are partial mappings. Test the exact operations your application needs in a non-production account; mocked unit tests are not live account certification.

## Amounts and idempotency

Use finite integer **provider minor units**, represented by `Decimal` where the interface requires it. `Decimal("1234")` is GBP 12.34. PayPal treats HUF, JPY and TWD as zero-decimal currencies, so `Decimal("1234")` means 1234 units there. HUF/TWD rules can differ across vendors: review amount conversion during provider migration. PayPal numeric fractional minor units and malformed response precision are rejected rather than rounded/truncated; Stripe and Square pass amounts through `int()`, which truncates fractions. Raw money strings are outside the common numeric amount convention: PayPal reads them as major-unit values and Square as minor units.

[PayPal's currency rules](https://developer.paypal.com/api/codes/currency/) define its zero-decimal behavior. Each provider controls supported currencies, account restrictions and API limits.

```python
from decimal import Decimal
intent = payments.create_payment_intent(
    amount=Decimal("1000"), currency="gbp",
    idempotency_key="your-application-defined-unique-operation-id",
)
```

Use stable, unique operation keys according to the provider's idempotency rules. Stripe payment/checkout methods keep the common positional idempotency argument; Stripe-specific options are keyword-only after it. Applications own retries, reconciliation, user authorization and duplicate-event tracking.

## Stripe catalog and webhooks

The Stripe adapter exposes `discover_catalog`, auto-paginated catalog helpers, mutable `update_price`, and explicit `replace_price` for immutable monetary/recurrence changes. Replacement transfers a lookup key; existing subscriptions and prior prices need explicit application migration/archival decisions. Entitlements feature/product attachment methods are provider-specific.

Webhook endpoint create/read/update/delete operations are explicit. The signing secret is returned only when created; discovery/read/update output omits it. Secure that one-time value yourself. Verify incoming signatures against raw request bytes, authorize event processing, and maintain durable idempotency/audit state. In-memory processed-event sets are not a distributed transaction store.

Applications own customer data, concrete Django models/migrations, payment authorization, refund approval, regulatory obligations and provider accounts. Runtime MCP does not execute production payment transactions; generated examples are text requiring application review.
