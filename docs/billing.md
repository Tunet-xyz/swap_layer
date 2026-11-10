# Billing

Use `get_provider("billing")` (`"payments"` is still accepted) with `billing.provider` set to `stripe`, `paypal`, or `square`. The modules are under `swap_layer.billing`, including customers, subscriptions, payment intents, products and provider implementations. Changing providers requires application and data review.

## Configure

```python
import os
from swap_layer import configure, get_provider
configure(billing={"provider":"stripe", "stripe":{
    "secret_key": os.environ["STRIPE_SECRET_KEY"],
    "webhook_secret": os.environ.get("STRIPE_WEBHOOK_SECRET"),
}})
billing = get_provider("billing")
```

Install `SwapLayer[stripe]` for Stripe 16.x. PayPal and Square use the core Requests dependency. In Django, use the same structure as `SWAPLAYER` or a `SwapLayerSettings` instance. Legacy `PAYMENT_PROVIDER` and provider key settings remain supported.

PayPal configuration is `billing={'provider':'paypal','paypal':{'client_id':...,'client_secret':...,'webhook_id':...,'sandbox':True}}`. Square uses `billing={'provider':'square','square':{'access_token':...,'location_id':...,'webhook_signature_key':...,'webhook_notification_url':...,'sandbox':True}}`. Read credentials from the caller's environment. A test label does not switch credentials to sandbox mode automatically.

## Capability boundaries

| Surface | Stripe | PayPal / Square |
| --- | --- | --- |
| Customers, payments, products, prices, subscriptions, checkout, invoices, refunds | Provider adapter operations | Provider-specific mappings and limitations |
| Metered billing, promotion codes, tax-rate objects, hosted billing portal | Broad Stripe surface | Unsupported Stripe-specific operations raise validation errors |
| Entitlements and catalog discovery | Stripe-specific extensions | No equivalent common guarantee |
| Webhook verification | Stripe signature and endpoint secret | PayPal verification API with the `PAYPAL-*` headers; Square signature (with the notification URL) and a signed `created_at` |

PayPal `verify_webhook_signature(payload, signature, headers=request.headers)` reads `PAYPAL-AUTH-ALGO`, `PAYPAL-CERT-URL`, `PAYPAL-TRANSMISSION-ID`, `PAYPAL-TRANSMISSION-SIG` and `PAYPAL-TRANSMISSION-TIME` from the request headers (Django's `request.headers` or `request.META`), using `signature` as the transmission signature when the headers lack it; a missing header raises. It requires a `webhook_id` (configured, or passed as `webhook_secret`) and fails closed: any verification status other than `SUCCESS` raises.

Square `verify_webhook_signature` also needs the event's signed `created_at`: at most 25 hours old (Square retries deliveries for 24 hours) and at most 5 minutes in the future. Construct `SquarePaymentProvider(..., webhook_max_age=None)` to turn the age check off. Keep processed `event_id` values for at least 25 hours and pass them to `dispatch_webhook_event(event, handlers, processed_event_ids=...)`.

PayPal has no customer object: the customer methods manage a local handle, `paypal:<email>`, which `create_subscription` uses as the subscriber. Their results carry `"local_only": True`, and remote PayPal payer IDs cannot be updated or deleted through them. PayPal's `create_billing_portal_session` raises `PaymentValidationError`: PayPal has no hosted billing portal.

Normalized objects include provider IDs and status fields; IDs cannot be moved between accounts/vendors by changing configuration. Some provider-specific invoice/customer operations are partial mappings. Test the exact operations your application needs in a non-production account; mocked unit tests are not live account certification.

## Amounts and idempotency

Use finite integer **provider minor units**, represented by `Decimal` where the interface requires it. `Decimal("1234")` is GBP 12.34. PayPal treats HUF, JPY and TWD as zero-decimal currencies, so `Decimal("1234")` means 1234 units there. HUF/TWD rules can differ across vendors: review amount conversion during provider migration. A fraction of a minor unit raises `PaymentValidationError` with every provider rather than being rounded or truncated, and PayPal also rejects malformed response precision. Raw money strings are outside the common numeric amount convention: PayPal reads them as major-unit values, and Stripe and Square read an integral string as minor units.

[PayPal's currency rules](https://developer.paypal.com/api/codes/currency/) define its zero-decimal behavior. Each provider controls supported currencies, account restrictions and API limits.

```python
from decimal import Decimal
intent = billing.create_payment_intent(
    amount=Decimal("1000"), currency="gbp",
    idempotency_key="your-application-defined-unique-operation-id",
)
```

Use stable, unique operation keys according to the provider's idempotency rules. Stripe payment/checkout methods keep the common positional idempotency argument; Stripe-specific options are keyword-only after it. Applications own retries, reconciliation, user authorization and duplicate-event tracking.

## Stripe catalog and webhooks

The Stripe adapter exposes `discover_catalog`, auto-paginated catalog helpers, mutable `update_price`, and explicit `replace_price` for immutable monetary/recurrence changes. Replacement transfers a lookup key; existing subscriptions and prior prices need explicit application migration/archival decisions. Entitlements feature/product attachment methods are provider-specific.

Webhook endpoint create/read/update/delete operations are explicit. The signing secret is returned only when created; discovery/read/update output omits it. Secure that one-time value yourself. Verify incoming signatures against raw request bytes, authorize event processing, and maintain durable idempotency/audit state. In-memory processed-event sets are not a distributed transaction store.

Applications own customer data, concrete Django models/migrations, payment authorization, refund approval, regulatory obligations and provider accounts. Runtime MCP does not execute production payment transactions; generated examples are text requiring application review.
