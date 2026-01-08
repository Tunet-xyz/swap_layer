# SwapLayer
### The Anti-Vendor-Lock-in Framework for Django

[![Version](https://img.shields.io/badge/version-1.0.0--rc1-blue.svg)](https://github.com/Tunet-xyz/swap_layer/releases)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/django-4.2%2B-green.svg)](https://www.djangoproject.com/)

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
pip install swaplayer
```

Or with specific extras:
```bash
# For Stripe payments
pip install swaplayer[stripe]

# For email with anymail
pip install swaplayer[email]

# For SMS with Twilio
pip install swaplayer[sms]

# For identity/auth providers
pip install swaplayer[identity]

# For all features
pip install swaplayer[all]
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
| **Email** | ✅ Production | Django SMTP, Anymail (SendGrid, Mailgun, SES, etc.) |
| **Payments** | ✅ Production | Stripe (PayPal planned) |
| **SMS** | ✅ Production | Twilio, AWS SNS |
| **Storage** | ✅ Production | Local, Django-storages (S3, Azure, GCS) |
| **Identity** | ✅ Beta | OAuth/SSO (WorkOS, Auth0) |
| **Verification** | ✅ Beta | KYC (Stripe Identity) |

**Note:** Beta modules are production-ready but may have minor API changes in v1.1+

---

## 📚 Full Documentation

**[→ docs/](docs/) - One doc per module:**

- **[Email](docs/email.md)** - Email providers
- **[Billing](docs/billing.md)** - Payment processing
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

## 🚀 Release Status

**Current Version:** 1.0.0-rc1 (Release Candidate)

This is the first public release candidate. All production modules are stable and ready for use:
- ✅ **107/109 tests passing** (98% pass rate)
- ✅ All core providers working in production
- ✅ Comprehensive error handling and validation
- ✅ Thread-safe implementations

### Known Limitations
- 2 WorkOS tests fail due to recent API changes (does not affect functionality)
- Identity modules are marked as Beta (production-ready, but APIs may evolve)
- Some linting warnings (B904 - exception chaining) are informational only

---

## License

MIT - Because avoiding vendor lock-in should be free.

---

**[→ Read Full Documentation](docs/README.md)**
