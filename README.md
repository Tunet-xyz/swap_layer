# SwapLayer
### The Anti-Vendor-Lock-in Framework for Django

**One Interface. Any Provider. Zero Rewrites.**

---

## What is SwapLayer?

SwapLayer is a **unified infrastructure layer** for Django that protects you from vendor lock-in.

Instead of coupling your code directly to Stripe, AWS, or Twilio, you write against **one consistent interface** and swap providers by changing a single configuration line.

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

```bash
pip install swap-layer[stripe,sendgrid,twilio]
```

### 2. Configure

```python
# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    email={'provider': 'django'},
    payments={'provider': 'stripe', 'stripe': {'secret_key': '...'}},
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

## Features

| Module | Status | Description |
|--------|--------|-------------|
| **Email** | ✅ Production | SMTP, SendGrid, Mailgun, SES |
| **Payments** | ✅ Production | Stripe (PayPal planned) |
| **SMS** | ✅ Production | Twilio, AWS SNS |
| **Storage** | ✅ Production | S3, Azure, GCS, Local |
| **Identity** | 🚧 Beta | OAuth/SSO, KYC Verification |

---

## 📚 Full Documentation

**[→ docs/](docs/) - One doc per module:**

- **[Email](docs/email.md)** - Email providers
- **[Payments](docs/payments.md)** - Payment processing
- **[SMS](docs/sms.md)** - SMS messaging
- **[Storage](docs/storage.md)** - File storage
- **[Identity Platform](docs/identity-platform.md)** - OAuth/SSO
- **[Identity Verification](docs/identity-verification.md)** - KYC
- **[Architecture](docs/architecture.md)** - Design patterns
- **[Contributing](docs/development/contributing.md)** - Help improve SwapLayer

---

## Why SwapLayer?

✅ **Avoid Vendor Lock-in** - Never get trapped by a single provider  
✅ **Consistent Interface** - Same API across all vendors  
✅ **Type Safe** - Pydantic validation catches errors early  
✅ **Battle Tested** - Wraps proven tools (django-storages, django-anymail)  
✅ **Zero Rewrites** - Swap providers with configuration changes only  

---

## License

MIT - Because avoiding vendor lock-in should be free.

---

**[→ Read Full Documentation](docs/index.md)**
