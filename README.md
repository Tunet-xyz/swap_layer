# SwapLayer
### The Anti-Vendor-Lock-in Framework for Django

**One Interface. Any Provider. Zero Rewrites.**

Part of the [Tunet](https://github.com/Tunet-xyz) ecosystem — alongside [SessionArmor](https://github.com/Tunet-xyz/session_armor) and [GeoCanon](https://github.com/Tunet-xyz/geo_canon).

---

## What is SwapLayer?

SwapLayer is a **unified infrastructure layer** for Django that protects you from vendor lock-in.

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
---

## Features

| Module | Status | Description |
|--------|--------|-------------|
| **Email** | ✅ Production | SMTP, SendGrid, Mailgun, SES |
| **Payments** | ✅ Production | Stripe, PayPal, Square |
| **SMS** | ✅ Production | Twilio, AWS SNS |
| **Storage** | ✅ Production | S3, Azure, GCS, Local — with scoped tenant isolation |
| **Identity** | ✅ Production | OAuth/SSO (WorkOS, Auth0), KYC Verification (Stripe Identity) |
| **MCP Server** | ✅ Production | AI Assistant Integration |

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

## License

MIT — Copyright (c) 2024-2026 Tunet Ltd. See [LICENSE](LICENSE).

---

**[→ Read Full Documentation](docs/README.md)**
