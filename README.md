# SwapLayer
### The Anti-Vendor-Lock-in Framework for Python Apps

**One Interface. Any Provider. Zero Rewrites.**

Part of the [Tunet](https://tunet.xyz/engineering/) ecosystem — alongside [SessionArmor](https://github.com/Tunet-xyz/session_armor) and [GeoCanon](https://github.com/Tunet-xyz/GeoCanon). See the [SwapLayer product page](https://tunet.xyz/engineering/swap-layer/) for the public capability overview.

---

## What is SwapLayer?

SwapLayer is a **unified infrastructure layer** for Python apps that protects you from vendor lock-in. It now has a framework-neutral core with Django and FastAPI integration adapters.

Instead of coupling your code directly to Stripe, PayPal, Square, AWS, or Twilio, you write against **one consistent interface** and swap providers by changing a single configuration line.

### The Problem

```python
# ❌ Tightly coupled - if Stripe fails, you rewrite everything
import stripe
customer = stripe.Customer.create(email='user@example.com')
```

### The Solution

```python
# ✅ Provider-agnostic - swap providers in settings
from swap_layer import get_provider
payments = get_provider('payments')
customer = payments.create_customer(email='user@example.com')
```

---

## Quick Start

### 1. Install

SwapLayer has optional dependencies - install only what you need:

```bash
# Core package
pip install swaplayer

# Framework adapters
pip install swaplayer[django]        # Django integration
pip install swaplayer[fastapi]       # FastAPI integration

# Install with specific providers
pip install swaplayer[stripe]        # Stripe billing
pip install swaplayer[paypal]        # PayPal billing
pip install swaplayer[square]        # Square billing
pip install swaplayer[identity]      # Just WorkOS/Auth0
pip install swaplayer[email,sms]     # Email + SMS

# Or install everything
pip install swaplayer[all]
```

**Available extras:**
- `django` - Django settings/admin/model integrations
- `fastapi` - FastAPI configuration adapter
- `stripe` - Stripe payment processing
- `paypal` - PayPal payment processing
- `square` - Square payment processing
- `identity` - WorkOS/Auth0 OAuth/SSO
- `email` - Enhanced email (django-anymail)
- `sms` - Twilio/AWS SNS messaging
- `aws` - AWS services (S3, SNS)
- `mcp` - AI assistant integration
- `all` - Everything

### 2. Configure

```python
# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    email={'provider': 'django'},
    billing={'provider': 'stripe', 'stripe': {'secret_key': 'sk_test_...'}},
    sms={'provider': 'twilio', 'twilio': {'account_sid': '...'}},
    storage={'provider': 'django'},
)
```

### 3. Use Anywhere

```python
from swap_layer import get_provider

# Email
get_provider('email').send(to='user@example.com', subject='Hello')

# Payments  
get_provider('payments').create_customer(email='user@example.com')

# SMS
get_provider('sms').send(to='+1555555', message='Welcome!')
```

---


### PayPal Billing

```python
SWAPLAYER = SwapLayerSettings(
    billing={
        'provider': 'paypal',
        'paypal': {
            'client_id': os.environ['PAYPAL_CLIENT_ID'],
            'client_secret': os.environ['PAYPAL_CLIENT_SECRET'],
            'webhook_id': os.environ.get('PAYPAL_WEBHOOK_ID'),
            'sandbox': True,
        },
    }
)
```

PayPal supports provider-agnostic products, plans, subscriptions, checkout orders, invoices, refunds, and webhook verification. It does not have direct equivalents for Stripe billing meters, Stripe coupons/promotion codes, Stripe tax-rate objects, or Stripe's hosted customer billing portal, so SwapLayer raises clear validation errors for those methods when PayPal is selected.

### Square Billing

```python
SWAPLAYER = SwapLayerSettings(
    billing={
        'provider': 'square',
        'square': {
            'access_token': os.environ['SQUARE_ACCESS_TOKEN'],
            'location_id': os.environ['SQUARE_LOCATION_ID'],
            'webhook_signature_key': os.environ.get('SQUARE_WEBHOOK_SIGNATURE_KEY'),
            'webhook_notification_url': os.environ.get('SQUARE_WEBHOOK_NOTIFICATION_URL'),
            'sandbox': True,
        },
    }
)
```

Square supports provider-agnostic customers, payments, catalog products/prices, subscriptions, checkout payment links, invoices, refunds, and webhook verification. Stripe remains the richest provider for metered usage, coupons/promotion codes, tax-rate management, and the hosted billing portal.

### Stripe Catalog Administration

SwapLayer is the single Stripe integration boundary for catalog discovery and mutation. Control
planes can use the Stripe provider to auto-page the full products, prices, billing-meter, and
Entitlements catalog, then create or update resources without importing Stripe directly:

```python
from swap_layer.billing.providers.stripe import StripePaymentProvider

stripe_billing = StripePaymentProvider(secret_key=os.environ["STRIPE_SECRET_KEY"])
catalog = stripe_billing.discover_catalog()

stripe_billing.update_price(
    "price_...",
    nickname="Professional monthly",
    idempotency_key="catalog-professional-monthly",
)
```

Immutable monetary or recurrence changes use `replace_price()`. It transfers the stable lookup
key to a new price and deliberately leaves the previous price and existing subscriptions untouched.

Control planes can also read aggregate revenue without ever touching customer data.
`discover_revenue(month="YYYY-MM")` sums one calendar month of paid-invoice amounts per price
lookup key and returns only `{lookup_key, currency, amount_minor}` lines — aggregation happens
inside SwapLayer, so no customer, invoice, or payment identifiers cross the boundary:

```python
revenue = stripe_billing.discover_revenue(month="2026-07")
# {"month": "2026-07", "lines": [
#   {"lookup_key": "tunet.micro.career.professional.usd.monthly", "currency": "usd", "amount_minor": 4800},
# ]}
```
---

## Features

| Module | Status | Description |
|--------|--------|-------------|
| **Email** | Production | Direct SMTP plus Django-anymail for SendGrid, Mailgun, SES, Postmark, and similar providers |
| **Payments** | Production | Stripe, PayPal, and Square provider adapters |
| **SMS** | Production | Twilio and AWS SNS provider adapters |
| **Storage** | Production | Local files, direct GCS, and Django-storage backends for S3/Azure/GCS |
| **Identity** | Production | OAuth/SSO via WorkOS/Auth0 plus Stripe Identity verification |
| **MCP Server** | Production | Runtime `swaplayer-mcp` plus public-agent contract in `mcp/` |

Provider parity is explicit rather than implied: Stripe remains the richest billing adapter; PayPal and Square raise validation errors for unsupported Stripe-specific concepts. Cloud storage providers other than direct GCS are reached through Django's storage backend layer.

---

## 🤖 AI Assistant Integration

SwapLayer includes an **MCP (Model Context Protocol) server** that exposes provider management as tools for AI assistants:

```bash
# Install with MCP support
pip install 'swaplayer[mcp]'

# Run the MCP server
swaplayer-mcp
```

**AI assistants can now help you:**
- Configure and switch providers through conversation
- Send test emails/SMS to verify integrations  
- Get provider setup instructions and capabilities
- Inspect your current configuration

Perfect for AI-powered development workflows! **[→ MCP Documentation](docs/mcp.md)**

---

## 📚 Full Documentation

**[→ docs/](docs/) - One doc per module:**

- **[Email](docs/email.md)** - Email providers
- **[Billing](docs/billing.md)** - Payment processing
- **[SMS](docs/sms.md)** - SMS messaging
- **[Storage](docs/storage.md)** - File storage
- **[Identity Platform](docs/identity-platform.md)** - OAuth/SSO
- **[Identity Verification](docs/identity-verification.md)** - KYC
- **[MCP Server](docs/mcp.md)** - AI assistant integration
- **[Architecture](docs/architecture.md)** - Design patterns
- **[Contributing](docs/development/contributing.md)** - Help improve SwapLayer

---

## Why SwapLayer?

✅ **Avoid Vendor Lock-in** - Never get trapped by a single provider  
✅ **Consistent Interface** - Same API across all vendors  
✅ **Type Safe** - Pydantic validation catches errors early  
✅ **Battle Tested** - Wraps proven tools (django-storages, django-anymail)  
✅ **Zero Rewrites** - Swap providers with configuration changes only  
✅ **AI-Powered** - Built-in MCP server for AI assistant integration

---


## Public Agent MCP Contract

SwapLayer now includes a public agent-operability contract in [`mcp/`](mcp/). It describes what external agents can safely discover and operate through published package APIs, `swaplayer-mcp`, public docs, and browser-visible surfaces without requiring source-code access or secrets.
## License

MIT — Copyright (c) 2024-2026 Tunet Ltd. See [LICENSE](LICENSE).

---

**[→ Read Full Documentation](docs/README.md)**
