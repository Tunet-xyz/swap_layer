"""
MCP Server implementation for SwapLayer.

Provides tools for AI assistants to interact with SwapLayer providers,
including onboarding, documentation, and configuration tools.
"""

import json
import pathlib
import uuid
from typing import Any

try:
    import mcp.types as types

    from mcp.server import Server

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    Server = None  # type: ignore

# Sensitive keys that should be redacted from configuration output
SENSITIVE_KEYS = {
    "secret_key",
    "api_key",
    "password",
    "token",
    "account_sid",
    "auth_token",
    "client_secret",
}

# Path to the docs directory — only available when running from source
_DOCS_DIR = pathlib.Path(__file__).parent.parent.parent.parent / "docs"

# ---------------------------------------------------------------------------
# Onboarding knowledge base — embedded so tools work without Django or the
# docs directory being present (e.g. when SwapLayer is installed as a package)
# ---------------------------------------------------------------------------

_EXPLAIN_TOPICS: dict[str, str] = {
    "overview": """# SwapLayer Overview

SwapLayer (also called "swap_lawyer") is an **anti-vendor-lock-in framework for Django** that
provides a unified abstraction layer over multiple third-party service providers.

## What it does

Instead of writing provider-specific code in your business logic, you use SwapLayer's consistent
API. Switching from one provider to another is a single config change — no code rewrite.

## Services covered

| Service | Providers |
|---------|-----------|
| Email | Django built-in, SMTP, SendGrid, Mailgun, AWS SES |
| Payments / Billing | Stripe, PayPal, Square |
| SMS | Twilio, AWS SNS |
| File Storage | Local filesystem, AWS S3, Azure Blob, Google Cloud Storage |
| Identity / SSO | WorkOS, Auth0 |
| Identity Verification (KYC) | Stripe Identity, Persona |

## Core API

```python
from swap_layer import get_provider

# Works for any service — the same call regardless of which provider is configured
email = get_provider('email')
email.send_email(to=['user@example.com'], subject='Hi', text_body='Hello!')

payments = get_provider('payments')
customer = payments.create_customer(email='user@example.com')

storage = get_provider('storage')
storage.save('uploads/photo.jpg', file_bytes)
```

## Why use SwapLayer?

- **Provider independence** — business logic never depends on Stripe, Twilio, etc. directly
- **Easy testing** — mock at the SwapLayer level, not at the SDK level
- **Future-proof** — add or swap providers with one config line
- **Consistent error handling** — all providers raise the same exception hierarchy
- **Security** — API keys are automatically redacted from error messages and logs
""",
    "philosophy": """# SwapLayer Design Philosophy

## The Problem: Vendor Lock-in

When you write:

```python
import stripe
customer = stripe.Customer.create(email='user@example.com')
subscription = stripe.Subscription.create(customer=customer.id, items=[{'price': 'price_xxx'}])
```

… your entire application is coupled to Stripe. Migrating to PayPal means rewriting every
call site. This is vendor lock-in.

## The SwapLayer Solution

SwapLayer provides a **provider-agnostic interface** for each service category:

```python
from swap_layer import get_provider

# Provider-agnostic — works with Stripe, PayPal, or Square
payments = get_provider('payments')
customer = payments.create_customer(email='user@example.com')
subscription = payments.create_subscription(customer_id=customer['id'], price_id='price_xxx')
```

Changing from Stripe to PayPal is one line in your Django settings — your application code
doesn't change at all.

## Design Principles

1. **One interface, any provider** — each service category has a single abstract interface
2. **Configuration over code** — provider selection happens in `settings.py`, not in imports
3. **Lazy loading** — provider SDKs are only imported when that provider is actually configured
4. **Fail loud** — configuration errors are caught at startup with descriptive messages
5. **Secrets stay secret** — sensitive values are never included in error messages or logs
6. **Standard dict returns** — all providers return plain Python dicts (no proprietary objects)
""",
    "architecture": """# SwapLayer Architecture

## Provider Adapter Pattern

SwapLayer uses the **Provider Adapter Pattern** across all services. Each service follows
the same structure:

```
src/swap_layer/{service}/
├── adapter.py       ← Abstract base class defining the interface
├── factory.py       ← Factory function that returns the configured provider
└── providers/
    ├── provider_a.py  ← Concrete implementation for provider A
    └── provider_b.py  ← Concrete implementation for provider B
```

## How a request flows

```
get_provider('email')
    │
    ▼
factory.py: get_email_provider()
    │  reads SWAPLAYER.email.provider from Django settings
    │
    ▼
providers/sendgrid.py: SendGridEmailProvider()
    │  implements EmailProviderAdapter
    │
    ▼
Your code: provider.send_email(...)
    │  calls the SendGrid-specific implementation
    │
    ▼
SendGrid API
```

## Abstract interfaces (adapters)

Each service has an abstract base class. All providers implement the same methods:

- **EmailProviderAdapter**: `send_email()`, `send_template_email()`, `send_bulk_email()`,
  `verify_email()`, `get_send_statistics()`, `add_to_suppression_list()`,
  `validate_webhook_signature()`

- **PaymentProviderAdapter** (composed of 4 sub-adapters):
  - CustomerAdapter: `create_customer()`, `get_customer()`, `update_customer()`, `delete_customer()`
  - SubscriptionAdapter: `create_subscription()`, `cancel_subscription()`, `update_subscription()`
  - PaymentAdapter: `create_payment_intent()`, `confirm_payment()`, `refund_payment()`
  - ProductAdapter: `create_product()`, `create_price()`, `list_products()`

- **SMSProviderAdapter**: `send_sms()`, `send_bulk_sms()`, `get_message_status()`,
  `validate_phone_number()`, `opt_out_number()`, `opt_in_number()`

- **StorageProviderAdapter**: `upload_file()`, `download_file()`, `delete_file()`,
  `file_exists()`, `list_files()`, `get_file_url()`, `generate_presigned_upload_url()`,
  `copy_file()`, `move_file()`

- **AuthProviderAdapter**: `get_authorization_url()`, `exchange_code_for_user()`,
  `get_logout_url()`, `clear_session()`

- **IdentityVerificationProviderAdapter**: `create_verification_session()`,
  `get_verification_session()`, `cancel_verification_session()`,
  `get_verification_report()`, `handle_webhook()`

## Configuration model

SwapLayer reads a single `SWAPLAYER` object from Django settings:

```python
# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    email={'provider': 'sendgrid', 'sendgrid': {'api_key': '...'}},
    payments={'provider': 'stripe', 'stripe': {'secret_key': '...'}},
)
```

Pydantic validates the configuration at import time and raises descriptive errors for
any missing or invalid fields.
""",
    "installation": """# SwapLayer Installation

## Base install

```bash
pip install SwapLayer
```

This installs the core package with Django and Pydantic support. You also need
provider-specific extras for third-party integrations.

## Extras by service

```bash
# Email (SendGrid, Mailgun, AWS SES)
pip install 'SwapLayer[email]'

# Payments (Stripe)
pip install 'SwapLayer[stripe]'

# SMS + Storage using AWS (Twilio SMS, S3 storage, SNS SMS)
pip install 'SwapLayer[sms]'
pip install 'SwapLayer[aws]'

# Azure Blob Storage
pip install 'SwapLayer[azure]'

# Identity / SSO (WorkOS, Auth0)
pip install 'SwapLayer[identity]'

# MCP server for AI assistant integration
pip install 'SwapLayer[mcp]'

# Everything at once
pip install 'SwapLayer[all]'
```

## Minimum Django settings

```python
# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    email={'provider': 'sendgrid', 'sendgrid': {'api_key': 'YOUR_KEY'}},
    # Add only the services you need
)
```

## Verify installation

```python
from swap_layer import get_provider, validate_swaplayer_config

# Check configuration is valid
validate_swaplayer_config()

# Get a provider
email = get_provider('email')
print(type(email))  # <class 'swap_layer.communications.email.providers.sendgrid.SendGridEmailProvider'>
```

## Running the MCP server

```bash
# After installing SwapLayer[mcp]
swaplayer-mcp

# Or via Python
python -m swap_layer.mcp
```
""",
    "django-integration": """# SwapLayer Django Integration

## Setup

### 1. Install

```bash
pip install 'SwapLayer[email,stripe,sms]'  # adjust extras for your providers
```

### 2. Configure settings.py

```python
# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    email={
        'provider': 'sendgrid',
        'sendgrid': {
            'api_key': env('SENDGRID_API_KEY'),  # use django-environ or python-decouple
        }
    },
    payments={
        'provider': 'stripe',
        'stripe': {
            'secret_key': env('STRIPE_SECRET_KEY'),
            'publishable_key': env('STRIPE_PUBLISHABLE_KEY'),
        }
    },
    sms={
        'provider': 'twilio',
        'twilio': {
            'account_sid': env('TWILIO_ACCOUNT_SID'),
            'auth_token': env('TWILIO_AUTH_TOKEN'),
            'from_number': env('TWILIO_FROM_NUMBER'),
        }
    },
)
```

### 3. Use in views, tasks, signals

```python
# views.py
from swap_layer import get_provider

def signup_view(request):
    # ... create user ...
    email = get_provider('email')
    email.send_email(
        to=[user.email],
        subject='Welcome!',
        text_body='Thanks for signing up.',
    )

# tasks.py (Celery)
from swap_layer import get_provider

@shared_task
def send_invoice(customer_id, amount):
    payments = get_provider('payments')
    intent = payments.create_payment_intent(
        amount=amount,
        currency='usd',
        customer_id=customer_id,
    )
    return intent['id']
```

## Environment variables (recommended)

Store credentials in `.env` and load with `django-environ` or `python-decouple`:

```bash
# .env
SENDGRID_API_KEY=SG.your_key_here
STRIPE_SECRET_KEY=sk_live_your_key_here
STRIPE_PUBLISHABLE_KEY=pk_live_your_key_here
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+15555551234
```

## Testing

```python
# tests/test_email.py
from unittest.mock import patch, MagicMock
from swap_layer import get_provider

def test_welcome_email_sent():
    mock_provider = MagicMock()
    with patch('swap_layer.get_provider', return_value=mock_provider):
        send_welcome_email('user@example.com', 'Alice')
    mock_provider.send_email.assert_called_once()
```
""",
    "security": """# SwapLayer Security Features

## Automatic secret redaction

SwapLayer automatically redacts sensitive values from all error messages, logs, and
MCP tool outputs. Secrets are replaced with `[REDACTED]`.

Redacted keys: `secret_key`, `api_key`, `password`, `token`, `account_sid`,
`auth_token`, `client_secret`

This means a misconfigured provider will give you:
```
ConfigurationError: Invalid Stripe config (api_key=[REDACTED])
```
instead of exposing your secret key.

## Pydantic validation

All configuration is validated by Pydantic models at import time. Missing required fields,
wrong types, or invalid values raise `ConfigurationError` immediately — before any provider
is used in production.

## Exception hierarchy

SwapLayer provides a consistent exception hierarchy:

```
SwapLayerError
├── ConfigurationError       — settings missing or invalid
│   ├── ProviderConfigMismatchError
│   ├── ModuleNotConfiguredError
│   └── EnvironmentVariableError
├── ValidationError          — input data invalid
└── ProviderError            — third-party API error
    ├── StripeKeyError
    ├── TwilioConfigError
    └── WorkOSConfigError
```

All exceptions include context without leaking secrets.

## MCP tool security

The `swaplayer_get_config` MCP tool strips all sensitive keys before returning configuration
data. API keys and tokens are never transmitted over MCP connections.
""",
    "providers": """# SwapLayer Providers Overview

## Email (6 providers)

| Provider | Extra | Best for |
|----------|-------|---------|
| `django` | none | Development, simple SMTP |
| `smtp` | none | Custom SMTP servers |
| `sendgrid` | `email` | Transactional email, analytics |
| `mailgun` | `email` | Developer-friendly, EU data |
| `ses` | `aws` | AWS-native, high volume, low cost |

## Payments / Billing (3 providers)

| Provider | Extra | Best for |
|----------|-------|---------|
| `stripe` | `stripe` | Subscriptions, SaaS billing, advanced features |
| `paypal` | none | Consumer payments, global reach |
| `square` | none | In-person + online, retail |

## SMS (2 providers)

| Provider | Extra | Best for |
|----------|-------|---------|
| `twilio` | `sms` | Reliability, global coverage, rich features |
| `sns` | `aws` | AWS-native apps, cost-effective at scale |

## File Storage (4 providers)

| Provider | Extra | Best for |
|----------|-------|---------|
| `local` / `django` | none | Development, single-server apps |
| `s3` | `aws` | AWS-native, most popular cloud storage |
| `azure` | `azure` | Azure-native, Microsoft ecosystem |
| `gcs` | none | Google Cloud-native apps |

## Identity / SSO (2 providers)

| Provider | Extra | Best for |
|----------|-------|---------|
| `workos` | `identity` | Enterprise SSO, SCIM, directory sync |
| `auth0` | `identity` | Consumer auth, social login, broad protocol support |

## Identity Verification / KYC (2 providers)

| Provider | Extra | Best for |
|----------|-------|---------|
| `stripe` | `stripe` | Stripe-native apps, integrated billing + KYC |
| `persona` | none | Advanced KYC/AML workflows, compliance-focused |
""",
    "faq": """# SwapLayer Frequently Asked Questions

**Q: Does SwapLayer replace the provider's native SDK?**
A: Yes — for the operations SwapLayer covers. You never import stripe, twilio, boto3, etc.
directly in your application code. SwapLayer imports them internally.

**Q: What if I need a provider feature that SwapLayer doesn't expose?**
A: Use the provider's native SDK directly for that specific feature. SwapLayer covers the
most common operations. Advanced or niche features can be accessed via the underlying SDK
alongside SwapLayer.

**Q: Does SwapLayer support async Django views?**
A: The current API is synchronous. Wrap calls with `sync_to_async` for async views:
```python
from asgiref.sync import sync_to_async
email = await sync_to_async(get_provider)('email')
```

**Q: How do I test code that uses SwapLayer providers?**
A: Mock at the provider level using `unittest.mock.patch`:
```python
with patch('swap_layer.get_provider') as mock_get:
    mock_get.return_value = MagicMock()
    # your test
```

**Q: Can I use multiple providers for the same service (e.g., two email providers)?**
A: Not directly through the standard API. One provider is active per service. For
multi-provider setups, instantiate providers directly from their factory functions.

**Q: Is SwapLayer production-ready?**
A: Yes. SwapLayer is used in production Django SaaS applications. Version 0.6.0 covers
email, payments, SMS, storage, identity, and verification.

**Q: Does SwapLayer work with Django REST Framework?**
A: Yes — SwapLayer is framework-agnostic within Django. It works with DRF, Django views,
Celery tasks, management commands, etc.

**Q: How do I report a bug or request a provider?**
A: Open an issue at https://github.com/Tunet-xyz/swap_layer/issues
""",
}

_PROVIDER_COMPARISONS: dict[str, dict[str, Any]] = {
    "email": {
        "summary": "Choose an email provider based on your volume, analytics needs, and infrastructure.",
        "providers": {
            "django": {
                "best_for": "Development and simple SMTP setups",
                "pros": [
                    "Zero extra dependencies",
                    "Uses Django's built-in email system",
                    "Easy local dev with console backend",
                ],
                "cons": ["No analytics or bounce handling", "Limited deliverability features"],
                "pip_extra": "none (base SwapLayer)",
                "credentials_needed": "Standard Django EMAIL_* settings",
                "recommended_when": "You're in development or using a basic SMTP relay",
            },
            "sendgrid": {
                "best_for": "Production transactional email with analytics",
                "pros": [
                    "Excellent deliverability",
                    "Rich analytics and tracking",
                    "Template management",
                    "Bounce/unsubscribe handling",
                ],
                "cons": ["Paid service (free tier available)", "US-based (GDPR considerations)"],
                "pip_extra": "SwapLayer[email]",
                "credentials_needed": "SENDGRID_API_KEY",
                "recommended_when": "You need reliable transactional email with analytics in production",
            },
            "mailgun": {
                "best_for": "Developer-friendly email with EU data residency option",
                "pros": [
                    "EU region available",
                    "Good deliverability",
                    "Simple API",
                    "Generous free tier",
                ],
                "cons": ["Slightly fewer analytics features than SendGrid"],
                "pip_extra": "SwapLayer[email]",
                "credentials_needed": "MAILGUN_API_KEY + MAILGUN_DOMAIN",
                "recommended_when": "You need EU data residency or prefer Mailgun's pricing",
            },
            "ses": {
                "best_for": "AWS-native applications at high volume",
                "pros": [
                    "Very low cost at scale",
                    "Native AWS integration",
                    "High deliverability when warmed up",
                ],
                "cons": [
                    "Requires SES sandbox exit process",
                    "Less beginner-friendly",
                    "Setup overhead",
                ],
                "pip_extra": "SwapLayer[aws]",
                "credentials_needed": "AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY + AWS region",
                "recommended_when": "You're already on AWS and need cost-effective high-volume email",
            },
        },
        "decision_guide": "Start with django for development. Use sendgrid or mailgun for production. Switch to ses if you're AWS-native and send at high volume.",
    },
    "payments": {
        "summary": "Choose a payment provider based on your business model, geography, and features needed.",
        "providers": {
            "stripe": {
                "best_for": "SaaS subscriptions, advanced billing, developer experience",
                "pros": [
                    "Best-in-class subscription management",
                    "Excellent docs",
                    "Billing portal",
                    "Tax calculation",
                    "Stripe Identity for KYC",
                ],
                "cons": ["Not available in all countries", "Can be expensive for high volume"],
                "pip_extra": "SwapLayer[stripe]",
                "credentials_needed": "STRIPE_SECRET_KEY + STRIPE_PUBLISHABLE_KEY",
                "recommended_when": "Building a SaaS with subscriptions — Stripe is the default choice",
            },
            "paypal": {
                "best_for": "Consumer payments, global reach, buyer trust",
                "pros": [
                    "Widely trusted by consumers",
                    "Available in 200+ countries",
                    "No credit card needed for buyers",
                ],
                "cons": [
                    "Less developer-friendly than Stripe",
                    "Higher fees for some transaction types",
                ],
                "pip_extra": "none (base SwapLayer)",
                "credentials_needed": "PAYPAL_CLIENT_ID + PAYPAL_CLIENT_SECRET",
                "recommended_when": "Your customers are consumers who prefer PayPal, or you need global coverage",
            },
            "square": {
                "best_for": "Businesses with in-person and online sales",
                "pros": [
                    "Excellent in-person POS integration",
                    "Good online payments",
                    "Invoicing",
                ],
                "cons": ["US/Canada focused", "Less subscription-focused than Stripe"],
                "pip_extra": "none (base SwapLayer)",
                "credentials_needed": "SQUARE_ACCESS_TOKEN + SQUARE_LOCATION_ID",
                "recommended_when": "You have a physical retail presence alongside your online store",
            },
        },
        "decision_guide": "For SaaS: use Stripe. For consumer e-commerce: consider PayPal. For retail+online: consider Square.",
    },
    "sms": {
        "summary": "Choose an SMS provider based on reliability needs, geography, and AWS integration.",
        "providers": {
            "twilio": {
                "best_for": "Reliability, global coverage, rich features",
                "pros": [
                    "Best deliverability globally",
                    "Excellent developer experience",
                    "Two-way messaging",
                    "Verify API for OTP",
                ],
                "cons": ["Higher cost than SNS", "Not AWS-native"],
                "pip_extra": "SwapLayer[sms]",
                "credentials_needed": "TWILIO_ACCOUNT_SID + TWILIO_AUTH_TOKEN + TWILIO_FROM_NUMBER",
                "recommended_when": "You need reliable global SMS — Twilio is the industry standard",
            },
            "sns": {
                "best_for": "AWS-native apps, cost-effective at scale",
                "pros": ["Lower cost at volume", "Native AWS integration", "No per-number cost"],
                "cons": [
                    "Less feature-rich than Twilio",
                    "One-way by default",
                    "Deliverability can vary by region",
                ],
                "pip_extra": "SwapLayer[aws]",
                "credentials_needed": "AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY + AWS region",
                "recommended_when": "You're already on AWS and send high-volume one-way notifications",
            },
        },
        "decision_guide": "Use Twilio for most cases. Switch to SNS if you're AWS-native and cost is a concern at high volume.",
    },
    "storage": {
        "summary": "Choose a storage provider based on your cloud infrastructure and compliance needs.",
        "providers": {
            "local": {
                "best_for": "Development and single-server deployments",
                "pros": ["Zero cost", "Zero configuration", "Instant setup"],
                "cons": ["Not suitable for multi-server or cloud deployments"],
                "pip_extra": "none (base SwapLayer)",
                "credentials_needed": "None — uses MEDIA_ROOT",
                "recommended_when": "Local development or a simple single-server app",
            },
            "s3": {
                "best_for": "AWS-native apps, most popular cloud storage",
                "pros": [
                    "Industry standard",
                    "Excellent durability and availability",
                    "Large ecosystem",
                    "CDN integration via CloudFront",
                ],
                "cons": ["AWS account required", "Complex IAM permissions"],
                "pip_extra": "SwapLayer[aws]",
                "credentials_needed": "AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY + S3_BUCKET_NAME",
                "recommended_when": "Default cloud storage choice, especially on AWS",
            },
            "azure": {
                "best_for": "Microsoft / Azure ecosystem",
                "pros": [
                    "Native Azure integration",
                    "Good compliance certifications",
                    "Azure CDN integration",
                ],
                "cons": ["Azure account required"],
                "pip_extra": "SwapLayer[azure]",
                "credentials_needed": "AZURE_STORAGE_ACCOUNT + AZURE_STORAGE_KEY + AZURE_CONTAINER_NAME",
                "recommended_when": "Your infrastructure is on Azure",
            },
            "gcs": {
                "best_for": "Google Cloud apps",
                "pros": ["Native GCP integration", "Strong performance", "Good pricing"],
                "cons": ["GCP account required"],
                "pip_extra": "none (uses google-cloud-storage)",
                "credentials_needed": "GCS credentials + GCS_BUCKET_NAME",
                "recommended_when": "Your infrastructure is on Google Cloud",
            },
        },
        "decision_guide": "Use local for development. S3 for AWS, Azure Blob for Microsoft, GCS for Google Cloud.",
    },
    "identity": {
        "summary": "Choose an identity provider based on your SSO requirements and target users.",
        "providers": {
            "workos": {
                "best_for": "Enterprise SSO, SCIM directory sync, B2B SaaS",
                "pros": [
                    "SAML, OIDC, Magic Link out of the box",
                    "SCIM user provisioning",
                    "Admin portal included",
                    "Audit log",
                ],
                "cons": [
                    "Paid (pricing per connection)",
                    "Enterprise-focused (overkill for consumer apps)",
                ],
                "pip_extra": "SwapLayer[identity]",
                "credentials_needed": "WORKOS_API_KEY + WORKOS_CLIENT_ID",
                "recommended_when": "Building B2B SaaS that needs enterprise SSO (Google Workspace, Okta, Azure AD)",
            },
            "auth0": {
                "best_for": "Consumer auth, social login, broad protocol support",
                "pros": [
                    "Social login (Google, GitHub, etc.)",
                    "MFA out of the box",
                    "Flexible rules/actions",
                    "Large community",
                ],
                "cons": ["Can get expensive at scale", "Complexity grows with features"],
                "pip_extra": "SwapLayer[identity]",
                "credentials_needed": "AUTH0_DOMAIN + AUTH0_CLIENT_ID + AUTH0_CLIENT_SECRET",
                "recommended_when": "Consumer-facing app needing social login and/or MFA",
            },
        },
        "decision_guide": "Use WorkOS for B2B/enterprise SSO. Use Auth0 for consumer auth with social login.",
    },
    "verification": {
        "summary": "Choose a KYC/identity verification provider based on your compliance workflow.",
        "providers": {
            "stripe": {
                "best_for": "Apps already using Stripe for payments",
                "pros": [
                    "Tight Stripe integration",
                    "Simple setup if already using Stripe billing",
                    "Good document verification",
                ],
                "cons": ["Less advanced KYC/AML workflows than Persona"],
                "pip_extra": "SwapLayer[stripe]",
                "credentials_needed": "STRIPE_SECRET_KEY (same as billing)",
                "recommended_when": "You use Stripe for payments and need basic identity verification",
            },
            "persona": {
                "best_for": "Advanced KYC/AML compliance workflows",
                "pros": [
                    "Highly configurable verification flows",
                    "AML screening",
                    "Compliance-focused",
                    "Good global coverage",
                ],
                "cons": ["More setup required", "Separate vendor from payments"],
                "pip_extra": "none (uses Persona API directly)",
                "credentials_needed": "PERSONA_API_KEY",
                "recommended_when": "You need advanced KYC, AML screening, or regulatory compliance workflows",
            },
        },
        "decision_guide": "Use Stripe Identity if already on Stripe. Use Persona for advanced compliance requirements.",
    },
}

_TROUBLESHOOT_SCENARIOS: dict[str, dict[str, Any]] = {
    "missing_config": {
        "symptoms": [
            "SwapLayerError: SWAPLAYER setting not found",
            "ModuleNotConfiguredError",
            "AttributeError: 'NoneType' object has no attribute",
        ],
        "cause": "The SWAPLAYER setting is not defined in Django settings.py",
        "solution": """Add the SWAPLAYER setting to your settings.py:

```python
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    email={'provider': 'sendgrid', 'sendgrid': {'api_key': 'YOUR_KEY'}},
    # add other services as needed
)
```

Make sure Django is configured before importing SwapLayer:
```python
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()
```""",
    },
    "missing_package": {
        "symptoms": [
            "ImportError: No module named 'stripe'",
            "ImportError: No module named 'twilio'",
            "ImportError: No module named 'sendgrid'",
        ],
        "cause": "The provider's SDK package is not installed",
        "solution": """Install the appropriate SwapLayer extra for your provider:

| Provider | Command |
|----------|---------|
| Stripe | `pip install 'SwapLayer[stripe]'` |
| SendGrid / Mailgun / SES | `pip install 'SwapLayer[email]'` |
| Twilio | `pip install 'SwapLayer[sms]'` |
| AWS (SNS, S3) | `pip install 'SwapLayer[aws]'` |
| Azure Blob | `pip install 'SwapLayer[azure]'` |
| WorkOS / Auth0 | `pip install 'SwapLayer[identity]'` |
| MCP server | `pip install 'SwapLayer[mcp]'` |

Or install everything: `pip install 'SwapLayer[all]'`""",
    },
    "invalid_credentials": {
        "symptoms": [
            "ProviderError: Authentication failed",
            "stripe.error.AuthenticationError",
            "TwilioConfigError",
            "StripeKeyError",
        ],
        "cause": "API key, token, or credentials are wrong or expired",
        "solution": """Check your credentials:

1. Verify environment variables are set:
```bash
echo $STRIPE_SECRET_KEY   # should start with sk_
echo $SENDGRID_API_KEY    # should start with SG.
echo $TWILIO_ACCOUNT_SID  # should start with AC
```

2. For Stripe: use test keys (sk_test_...) in development, live keys (sk_live_...) in production.

3. Confirm the key has the correct permissions in the provider dashboard.

4. Check for leading/trailing whitespace in environment variables.

5. Verify the key isn't expired or revoked in the provider dashboard.""",
    },
    "wrong_provider_name": {
        "symptoms": ["ConfigurationError: Unknown provider", "ValueError: Invalid provider"],
        "cause": "Provider name in configuration doesn't match an available provider",
        "solution": """Valid provider names by service:

| Service | Valid provider names |
|---------|---------------------|
| email | `django`, `smtp`, `sendgrid`, `mailgun`, `ses` |
| payments | `stripe`, `paypal`, `square` |
| sms | `twilio`, `sns` |
| storage | `local`, `django`, `s3`, `azure`, `gcs` |
| identity | `workos`, `auth0` |
| verification | `stripe`, `persona` |

Provider names are case-sensitive and lowercase. Example:
```python
SWAPLAYER = SwapLayerSettings(
    email={'provider': 'sendgrid', ...},  # correct
    # email={'provider': 'SendGrid', ...},  # WRONG - capital S
)
```""",
    },
    "django_not_setup": {
        "symptoms": [
            "django.core.exceptions.ImproperlyConfigured",
            "Apps aren't loaded yet",
            "django.setup() not called",
        ],
        "cause": "Django application registry isn't initialized before SwapLayer is used",
        "solution": """Ensure Django is set up before using SwapLayer:

```python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()  # must be called before get_provider()

from swap_layer import get_provider
email = get_provider('email')
```

In management commands or scripts, Django is set up automatically.
In tests, use `@pytest.mark.django_db` or configure pytest-django.""",
    },
    "mcp_not_installed": {
        "symptoms": ["ImportError: No module named 'mcp'", "Error: MCP dependencies not installed"],
        "cause": "The mcp package is not installed",
        "solution": """Install the MCP extra:

```bash
pip install 'SwapLayer[mcp]'
```

Then run the MCP server:
```bash
swaplayer-mcp
```

Or run directly:
```bash
python -m swap_layer.mcp
```""",
    },
}


def create_mcp_server() -> Any:
    """
    Create and configure the SwapLayer MCP server.

    Returns:
        Configured MCP Server instance

    Raises:
        ImportError: If mcp package is not installed
    """
    if not MCP_AVAILABLE:
        raise ImportError(
            "MCP server requires 'mcp' package. Install with: pip install 'SwapLayer[mcp]'"
        )

    server = Server("swaplayer")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        """List available SwapLayer tools."""
        return [
            # ── Operational tools (require configured Django + providers) ──────
            types.Tool(
                name="swaplayer_get_config",
                description="Get current SwapLayer configuration for a specific service or all services",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service type (email, payments, sms, storage, identity, verification) or 'all' for all services",
                            "enum": [
                                "all",
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        }
                    },
                    "required": ["service"],
                },
            ),
            types.Tool(
                name="swaplayer_list_providers",
                description="List available providers for a specific service type",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service type to list providers for",
                            "enum": [
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        }
                    },
                    "required": ["service"],
                },
            ),
            types.Tool(
                name="swaplayer_send_test_email",
                description="Send a test email using the configured email provider",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body (plain text)"},
                    },
                    "required": ["to", "subject", "body"],
                },
            ),
            types.Tool(
                name="swaplayer_send_test_sms",
                description="Send a test SMS using the configured SMS provider",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient phone number (E.164 format)",
                        },
                        "message": {"type": "string", "description": "SMS message text"},
                    },
                    "required": ["to", "message"],
                },
            ),
            types.Tool(
                name="swaplayer_check_storage",
                description="Check storage provider configuration and test connectivity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "test_upload": {
                            "type": "boolean",
                            "description": "Whether to perform a test file upload/delete",
                            "default": False,
                        }
                    },
                },
            ),
            types.Tool(
                name="swaplayer_get_provider_info",
                description="Get detailed information about a specific provider implementation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service type",
                            "enum": [
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        },
                        "provider": {
                            "type": "string",
                            "description": "Provider name (e.g., 'stripe', 'sendgrid', 'twilio')",
                        },
                    },
                    "required": ["service", "provider"],
                },
            ),
            types.Tool(
                name="swaplayer_generate_code",
                description="Generate code examples for using SwapLayer with specific operations and services",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service type to generate code for",
                            "enum": [
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        },
                        "operation": {
                            "type": "string",
                            "description": "Operation to perform (e.g., 'send_email', 'create_customer', 'upload_file')",
                        },
                        "context": {
                            "type": "string",
                            "description": "Optional context about the use case or requirements",
                        },
                    },
                    "required": ["service", "operation"],
                },
            ),
            types.Tool(
                name="swaplayer_get_usage_examples",
                description="Get common usage examples and patterns for a specific service",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service type to get examples for",
                            "enum": [
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Specific pattern or use case (e.g., 'welcome_email', 'subscription_flow', 'file_upload')",
                        },
                    },
                    "required": ["service"],
                },
            ),
            types.Tool(
                name="swaplayer_setup_quickstart",
                description="Generate complete quickstart configuration and setup code for SwapLayer with a specific service and provider. Returns Django settings configuration and installation instructions.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service type to set up",
                            "enum": [
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        },
                        "provider": {
                            "type": "string",
                            "description": "Provider to use (e.g., 'stripe', 'sendgrid', 'twilio', 's3')",
                        },
                        "project_type": {
                            "type": "string",
                            "description": "Type of Django project setup",
                            "enum": ["new", "existing"],
                            "default": "existing",
                        },
                    },
                    "required": ["service", "provider"],
                },
            ),
            # ── Onboarding tools (no Django / configured providers required) ───
            types.Tool(
                name="swaplayer_explain",
                description=(
                    "Explain SwapLayer concepts for onboarding. "
                    "Works without any Django project configured. "
                    "Use this first to understand what SwapLayer is and how it works."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Concept to explain",
                            "enum": [
                                "overview",
                                "philosophy",
                                "architecture",
                                "installation",
                                "django-integration",
                                "security",
                                "providers",
                                "faq",
                            ],
                        }
                    },
                    "required": ["topic"],
                },
            ),
            types.Tool(
                name="swaplayer_compare_providers",
                description=(
                    "Compare available providers for a SwapLayer service to help choose the right one. "
                    "Returns a decision guide with pros, cons, and recommendations. "
                    "Works without any Django project configured."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service to compare providers for",
                            "enum": [
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        },
                        "use_case": {
                            "type": "string",
                            "description": "Optional: describe your use case to get a more targeted recommendation (e.g. 'high-volume transactional email', 'SaaS subscriptions', 'EU data residency required')",
                        },
                    },
                    "required": ["service"],
                },
            ),
            types.Tool(
                name="swaplayer_troubleshoot",
                description=(
                    "Diagnose and resolve common SwapLayer configuration issues. "
                    "Provide an error message or symptom to get a targeted solution."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "scenario": {
                            "type": "string",
                            "description": "Known issue category",
                            "enum": [
                                "missing_config",
                                "missing_package",
                                "invalid_credentials",
                                "wrong_provider_name",
                                "django_not_setup",
                                "mcp_not_installed",
                            ],
                        },
                        "error_message": {
                            "type": "string",
                            "description": "Optional: paste the actual error message to get more context",
                        },
                    },
                    "required": ["scenario"],
                },
            ),
            types.Tool(
                name="swaplayer_get_migration_guide",
                description=(
                    "Get a step-by-step guide for migrating from one SwapLayer provider to another. "
                    "Shows exactly what configuration changes to make and confirms that application "
                    "code does NOT need to change."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service to migrate",
                            "enum": [
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        },
                        "from_provider": {
                            "type": "string",
                            "description": "Current provider (e.g., 'stripe', 'sendgrid', 'twilio')",
                        },
                        "to_provider": {
                            "type": "string",
                            "description": "Target provider to migrate to",
                        },
                    },
                    "required": ["service", "from_provider", "to_provider"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Any) -> list[types.TextContent]:
        """Handle tool calls."""
        try:
            if name == "swaplayer_get_config":
                result = await _get_config(arguments.get("service", "all"))
            elif name == "swaplayer_list_providers":
                result = await _list_providers(arguments["service"])
            elif name == "swaplayer_send_test_email":
                result = await _send_test_email(
                    arguments["to"], arguments["subject"], arguments["body"]
                )
            elif name == "swaplayer_send_test_sms":
                result = await _send_test_sms(arguments["to"], arguments["message"])
            elif name == "swaplayer_check_storage":
                result = await _check_storage(arguments.get("test_upload", False))
            elif name == "swaplayer_get_provider_info":
                result = await _get_provider_info(arguments["service"], arguments["provider"])
            elif name == "swaplayer_generate_code":
                result = await _generate_code(
                    arguments["service"], arguments["operation"], arguments.get("context", "")
                )
            elif name == "swaplayer_get_usage_examples":
                result = await _get_usage_examples(
                    arguments["service"], arguments.get("pattern", "")
                )
            elif name == "swaplayer_setup_quickstart":
                result = await _setup_quickstart(
                    arguments["service"],
                    arguments["provider"],
                    arguments.get("project_type", "existing"),
                )
            elif name == "swaplayer_explain":
                result = await _explain(arguments["topic"])
            elif name == "swaplayer_compare_providers":
                result = await _compare_providers(
                    arguments["service"], arguments.get("use_case", "")
                )
            elif name == "swaplayer_troubleshoot":
                result = await _troubleshoot(
                    arguments["scenario"], arguments.get("error_message", "")
                )
            elif name == "swaplayer_get_migration_guide":
                result = await _get_migration_guide(
                    arguments["service"],
                    arguments["from_provider"],
                    arguments["to_provider"],
                )
            else:
                raise ValueError(f"Unknown tool: {name}")

            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            error_result = {"error": str(e), "type": type(e).__name__}
            return [types.TextContent(type="text", text=json.dumps(error_result, indent=2))]

    # ── Resources — expose documentation for agents to read directly ──────────

    @server.list_resources()
    async def list_resources() -> list[types.Resource]:
        """List SwapLayer documentation resources."""
        resources = [
            types.Resource(
                uri="swaplayer://docs/overview",
                name="SwapLayer Overview",
                description="What SwapLayer is, what problems it solves, and the core API",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/architecture",
                name="Architecture Guide",
                description="Provider adapter pattern, service structure, and design decisions",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/email",
                name="Email Service Guide",
                description="Email providers, configuration, and usage examples",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/billing",
                name="Billing & Payments Guide",
                description="Payment providers, subscriptions, customers, and billing flows",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/sms",
                name="SMS Service Guide",
                description="SMS providers, configuration, and usage examples",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/storage",
                name="File Storage Guide",
                description="Storage providers, file upload/download, and URL generation",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/identity-platform",
                name="Identity Platform Guide",
                description="OAuth / SSO authentication providers",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/identity-verification",
                name="Identity Verification Guide",
                description="KYC / identity verification providers",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/mcp",
                name="MCP Server Guide",
                description="How to use SwapLayer's MCP server with AI assistants",
                mimeType="text/markdown",
            ),
        ]
        return resources

    @server.read_resource()
    async def read_resource(uri: Any) -> str:
        """Read a SwapLayer documentation resource."""
        uri_str = str(uri)

        # Map URIs to doc files
        doc_map = {
            "swaplayer://docs/overview": "README.md",
            "swaplayer://docs/architecture": "docs/architecture.md",
            "swaplayer://docs/email": "docs/email.md",
            "swaplayer://docs/billing": "docs/billing.md",
            "swaplayer://docs/sms": "docs/sms.md",
            "swaplayer://docs/storage": "docs/storage.md",
            "swaplayer://docs/identity-platform": "docs/identity-platform.md",
            "swaplayer://docs/identity-verification": "docs/identity-verification.md",
            "swaplayer://docs/mcp": "docs/mcp.md",
        }

        relative_path = doc_map.get(uri_str)
        if not relative_path:
            raise ValueError(f"Unknown resource URI: {uri_str}")

        # Try to read from the project root (works when running from source)
        doc_path = pathlib.Path(__file__).parent.parent.parent.parent / relative_path
        if doc_path.exists():
            return doc_path.read_text(encoding="utf-8")

        # Fall back to the embedded topic content for the overview
        topic_fallbacks = {
            "swaplayer://docs/overview": _EXPLAIN_TOPICS["overview"],
            "swaplayer://docs/architecture": _EXPLAIN_TOPICS["architecture"],
        }
        if uri_str in topic_fallbacks:
            return topic_fallbacks[uri_str]

        raise FileNotFoundError(
            f"Documentation file not found: {relative_path}. "
            "Run the MCP server from the SwapLayer project directory, or use "
            "swaplayer_explain / swaplayer_compare_providers tools instead."
        )

    # ── Prompts — reusable onboarding workflow templates ─────────────────────

    @server.list_prompts()
    async def list_prompts() -> list[types.Prompt]:
        """List SwapLayer onboarding prompt templates."""
        return [
            types.Prompt(
                name="onboard_service",
                description=(
                    "Walk through adding a new SwapLayer service to a Django project. "
                    "Covers installation, configuration, environment variables, and first use."
                ),
                arguments=[
                    types.PromptArgument(
                        name="service",
                        description="Service to set up (email, payments, sms, storage, identity, verification)",
                        required=True,
                    ),
                    types.PromptArgument(
                        name="provider",
                        description="Provider to use (e.g. stripe, sendgrid, twilio, s3)",
                        required=True,
                    ),
                ],
            ),
            types.Prompt(
                name="choose_provider",
                description=(
                    "Help choose the right SwapLayer provider for a service based on "
                    "requirements, budget, and infrastructure."
                ),
                arguments=[
                    types.PromptArgument(
                        name="service",
                        description="Service type (email, payments, sms, storage, identity, verification)",
                        required=True,
                    ),
                    types.PromptArgument(
                        name="requirements",
                        description="Key requirements or constraints (e.g. 'EU data residency', 'low cost', 'already on AWS')",
                        required=False,
                    ),
                ],
            ),
            types.Prompt(
                name="migrate_provider",
                description=(
                    "Guide a developer through migrating from one SwapLayer provider to another, "
                    "confirming that application code stays unchanged."
                ),
                arguments=[
                    types.PromptArgument(
                        name="service",
                        description="Service to migrate",
                        required=True,
                    ),
                    types.PromptArgument(
                        name="from_provider",
                        description="Current provider",
                        required=True,
                    ),
                    types.PromptArgument(
                        name="to_provider",
                        description="Target provider",
                        required=True,
                    ),
                ],
            ),
        ]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
        """Return a SwapLayer onboarding prompt."""
        args = arguments or {}

        if name == "onboard_service":
            service = args.get("service", "<service>")
            provider = args.get("provider", "<provider>")
            return types.GetPromptResult(
                description=f"Onboarding guide for SwapLayer {service} with {provider}",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=(
                                f"I want to add {service} support to my Django project using "
                                f"SwapLayer with the {provider} provider.\n\n"
                                f"Please:\n"
                                f"1. Call swaplayer_setup_quickstart(service='{service}', provider='{provider}') "
                                f"to get the installation and configuration steps\n"
                                f"2. Call swaplayer_generate_code(service='{service}', operation='send_{service}' "
                                f"or the most common operation) to show me a working code example\n"
                                f"3. Explain any gotchas or common mistakes to avoid\n"
                                f"4. Show me how to test it works without hitting the real API"
                            ),
                        ),
                    )
                ],
            )

        if name == "choose_provider":
            service = args.get("service", "<service>")
            requirements = args.get("requirements", "")
            requirements_text = f"\n\nMy requirements: {requirements}" if requirements else ""
            return types.GetPromptResult(
                description=f"Provider selection guide for SwapLayer {service}",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=(
                                f"I need to choose a {service} provider for my Django project "
                                f"using SwapLayer.{requirements_text}\n\n"
                                f"Please:\n"
                                f"1. Call swaplayer_compare_providers(service='{service}'"
                                + (f", use_case='{requirements}'" if requirements else "")
                                + ") to get a comparison\n"
                                "2. Recommend the best provider for my situation\n"
                                "3. Explain what I'd need to do to switch providers later if needed"
                            ),
                        ),
                    )
                ],
            )

        if name == "migrate_provider":
            service = args.get("service", "<service>")
            from_provider = args.get("from_provider", "<from>")
            to_provider = args.get("to_provider", "<to>")
            return types.GetPromptResult(
                description=f"Migration guide: {service} from {from_provider} to {to_provider}",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=(
                                f"I want to migrate my SwapLayer {service} configuration "
                                f"from {from_provider} to {to_provider}.\n\n"
                                f"Please:\n"
                                f"1. Call swaplayer_get_migration_guide(service='{service}', "
                                f"from_provider='{from_provider}', to_provider='{to_provider}') "
                                f"for the migration steps\n"
                                f"2. Confirm which parts of my application code will need to change "
                                f"(hint: it should be zero lines of application code)\n"
                                f"3. List any data migration considerations "
                                f"(e.g. customer IDs stored in the database)"
                            ),
                        ),
                    )
                ],
            )

        raise ValueError(f"Unknown prompt: {name}")

    return server


# ---------------------------------------------------------------------------
# Existing operational tool implementations
# ---------------------------------------------------------------------------


async def _get_config(service: str) -> dict[str, Any]:
    """Get SwapLayer configuration."""
    from swap_layer.settings import get_swaplayer_settings

    try:
        settings = get_swaplayer_settings()

        if service == "all":
            config = {}
            for svc in ["email", "payments", "sms", "storage", "identity", "verification"]:
                if hasattr(settings, svc):
                    svc_config = getattr(settings, svc)
                    if svc_config:
                        safe_config = {
                            k: v for k, v in svc_config.items() if k not in SENSITIVE_KEYS
                        }
                        config[svc] = safe_config
            return {"status": "success", "config": config}
        else:
            if hasattr(settings, service):
                svc_config = getattr(settings, service)
                if svc_config:
                    safe_config = {k: v for k, v in svc_config.items() if k not in SENSITIVE_KEYS}
                    return {"status": "success", "service": service, "config": safe_config}
            return {"status": "not_configured", "service": service}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _list_providers(service: str) -> dict[str, Any]:
    """List available providers for a service."""
    providers = {
        "email": ["django", "smtp", "sendgrid", "mailgun", "ses"],
        "payments": ["stripe", "paypal", "square"],
        "sms": ["twilio", "sns"],
        "storage": ["django", "s3", "azure", "gcs"],
        "identity": ["workos", "auth0"],
        "verification": ["workos", "persona"],
    }

    if service not in providers:
        return {"status": "error", "message": f"Unknown service: {service}"}

    return {"status": "success", "service": service, "providers": providers[service]}


async def _send_test_email(to: str, subject: str, body: str) -> dict[str, Any]:
    """Send a test email."""
    try:
        from swap_layer import get_provider

        email_provider = get_provider("email")
        result = email_provider.send_email(to=[to], subject=subject, text_body=body)

        return {"status": "success", "message": "Test email sent successfully", "result": result}
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to send test email: {str(e)}",
            "error_type": type(e).__name__,
        }


async def _send_test_sms(to: str, message: str) -> dict[str, Any]:
    """Send a test SMS."""
    try:
        from swap_layer import get_provider

        sms_provider = get_provider("sms")
        result = sms_provider.send_sms(to=to, message=message)

        return {"status": "success", "message": "Test SMS sent successfully", "result": result}
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to send test SMS: {str(e)}",
            "error_type": type(e).__name__,
        }


async def _check_storage(test_upload: bool = False) -> dict[str, Any]:
    """Check storage provider configuration."""
    try:
        from swap_layer import get_provider

        storage_provider = get_provider("storage")

        info = {
            "status": "success",
            "message": "Storage provider configured",
            "provider_type": type(storage_provider).__name__,
        }

        if test_upload:
            test_content = b"SwapLayer MCP test file"
            test_filename = f"mcp_test_{uuid.uuid4().hex[:8]}.txt"

            try:
                storage_provider.save(test_filename, test_content)
                storage_provider.delete(test_filename)
                info["test_upload"] = "success"
            except Exception as e:
                info["test_upload"] = "failed"
                info["test_error"] = str(e)

        return info
    except Exception as e:
        return {
            "status": "error",
            "message": f"Storage check failed: {str(e)}",
            "error_type": type(e).__name__,
        }


async def _get_provider_info(service: str, provider: str) -> dict[str, Any]:
    """Get information about a specific provider."""
    provider_info = {
        "email": {
            "django": {
                "description": "Django's built-in email backend",
                "capabilities": ["send_email"],
                "setup": "Uses Django EMAIL_* settings",
            },
            "sendgrid": {
                "description": "SendGrid email service",
                "capabilities": ["send_email", "templates", "tracking"],
                "setup": "Requires SENDGRID_API_KEY",
            },
            "mailgun": {
                "description": "Mailgun email service",
                "capabilities": ["send_email", "templates", "tracking"],
                "setup": "Requires MAILGUN_API_KEY and domain",
            },
            "ses": {
                "description": "Amazon SES",
                "capabilities": ["send_email", "templates"],
                "setup": "Requires AWS credentials",
            },
        },
        "payments": {
            "stripe": {
                "description": "Stripe payment processing and advanced billing",
                "capabilities": [
                    "customers",
                    "subscriptions",
                    "payment_intents",
                    "products",
                    "billing_meters",
                    "coupons",
                    "tax_rates",
                    "billing_portal",
                ],
                "setup": "Requires STRIPE_SECRET_KEY",
            },
            "paypal": {
                "description": "PayPal payments, orders, subscriptions, invoicing, and refunds",
                "capabilities": [
                    "customers",
                    "subscriptions",
                    "orders",
                    "products",
                    "plans",
                    "invoices",
                    "refunds",
                    "webhooks",
                ],
                "setup": "Requires PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET",
            },
            "square": {
                "description": "Square payments, catalog, subscriptions, checkout links, invoicing, and refunds",
                "capabilities": [
                    "customers",
                    "payments",
                    "catalog",
                    "subscriptions",
                    "checkout_links",
                    "invoices",
                    "refunds",
                    "webhooks",
                ],
                "setup": "Requires SQUARE_ACCESS_TOKEN and SQUARE_LOCATION_ID",
            },
        },
        "sms": {
            "twilio": {
                "description": "Twilio SMS service",
                "capabilities": ["send_sms"],
                "setup": "Requires TWILIO_ACCOUNT_SID and AUTH_TOKEN",
            },
            "sns": {
                "description": "Amazon SNS",
                "capabilities": ["send_sms"],
                "setup": "Requires AWS credentials",
            },
        },
        "storage": {
            "s3": {
                "description": "Amazon S3 storage",
                "capabilities": ["save", "delete", "url", "exists"],
                "setup": "Requires AWS credentials and bucket name",
            },
            "azure": {
                "description": "Azure Blob Storage",
                "capabilities": ["save", "delete", "url", "exists"],
                "setup": "Requires Azure credentials and container",
            },
            "gcs": {
                "description": "Google Cloud Storage",
                "capabilities": ["save", "delete", "url", "exists"],
                "setup": "Requires GCS credentials and bucket",
            },
        },
        "identity": {
            "workos": {
                "description": "WorkOS identity platform",
                "capabilities": ["oauth", "sso", "directory_sync"],
                "setup": "Requires WORKOS_API_KEY and CLIENT_ID",
            }
        },
    }

    if service not in provider_info:
        return {"status": "error", "message": f"Unknown service: {service}"}

    if provider not in provider_info[service]:
        return {
            "status": "error",
            "message": f"Unknown provider '{provider}' for service '{service}'",
        }

    return {
        "status": "success",
        "service": service,
        "provider": provider,
        "info": provider_info[service][provider],
    }


async def _generate_code(service: str, operation: str, context: str = "") -> dict[str, Any]:
    """Generate code examples for using SwapLayer."""
    code_templates = {
        "email": {
            "send_email": """# Send email using SwapLayer
from swap_layer import get_provider

email_provider = get_provider('email')
result = email_provider.send_email(
    to=['recipient@example.com'],
    subject='Your Subject Here',
    text_body='Plain text content',
    html_body='<h1>HTML content</h1>',  # optional
    from_email='sender@example.com'  # optional, uses default
)
print(f"Email sent: {result['message_id']}")""",
            "send_with_attachment": """# Send email with attachment
from swap_layer import get_provider

email_provider = get_provider('email')
result = email_provider.send_email(
    to=['recipient@example.com'],
    subject='Document Attached',
    text_body='Please find the attached document.',
    attachments=[
        {
            'filename': 'document.pdf',
            'content': open('path/to/document.pdf', 'rb').read(),
            'mimetype': 'application/pdf'
        }
    ]
)""",
        },
        "payments": {
            "create_customer": """# Create a customer
from swap_layer import get_provider

payments = get_provider('payments')
customer = payments.create_customer(
    email='customer@example.com',
    name='John Doe',
    metadata={'user_id': '12345'}
)
print(f"Customer created: {customer['id']}")""",
            "create_subscription": """# Create a subscription
from swap_layer import get_provider

payments = get_provider('payments')

# First create a customer
customer = payments.create_customer(email='customer@example.com')

# Then create a subscription
subscription = payments.create_subscription(
    customer_id=customer['id'],
    price_id='price_xxxxx',  # Your price ID from provider
    metadata={'plan': 'premium'}
)
print(f"Subscription created: {subscription['id']}")""",
            "create_payment_intent": """# Create a payment intent
from swap_layer import get_provider

payments = get_provider('payments')
intent = payments.create_payment_intent(
    amount=2000,  # Amount in cents
    currency='usd',
    customer_id='cus_xxxxx',  # optional
    metadata={'order_id': '12345'}
)
print(f"Payment intent: {intent['id']}")
print(f"Client secret: {intent['client_secret']}")""",
        },
        "sms": {
            "send_sms": """# Send SMS using SwapLayer
from swap_layer import get_provider

sms_provider = get_provider('sms')
result = sms_provider.send_sms(
    to='+15555551234',  # E.164 format
    message='Your verification code is: 123456'
)
print(f"SMS sent: {result['message_id']}")""",
        },
        "storage": {
            "upload_file": """# Upload file to storage
from swap_layer import get_provider

storage = get_provider('storage')

# Upload a file
with open('local_file.jpg', 'rb') as f:
    file_content = f.read()

storage.save('uploads/image.jpg', file_content)
url = storage.url('uploads/image.jpg')
print(f"File uploaded: {url}")""",
            "check_file_exists": """# Check if file exists
from swap_layer import get_provider

storage = get_provider('storage')

if storage.exists('uploads/image.jpg'):
    print("File exists")
    url = storage.url('uploads/image.jpg')
    print(f"URL: {url}")
else:
    print("File not found")""",
        },
        "identity": {
            "oauth_flow": """# OAuth authentication flow
from swap_layer import get_provider

# In your login view
identity = get_provider('identity')
auth_url = identity.get_authorization_url(
    request=request,
    redirect_uri='https://yourapp.com/callback',
    state='random_state_string'
)
return redirect(auth_url)

# In your callback view
user_data = identity.exchange_code_for_user(
    request=request,
    code=request.GET['code']
)
print(f"User logged in: {user_data['email']}")""",
        },
        "verification": {
            "create_verification": """# Create identity verification session
from swap_layer import get_provider

verification = get_provider('verification')
session = verification.create_verification_session(
    type='identity',
    metadata={'user_id': '12345'}
)
print(f"Verification URL: {session['url']}")
print(f"Session ID: {session['id']}")""",
        },
    }

    if service in code_templates and operation in code_templates[service]:
        code = code_templates[service][operation]
        return {
            "status": "success",
            "service": service,
            "operation": operation,
            "code": code,
            "language": "python",
        }

    generic_templates = {
        "email": "send_email",
        "payments": "create_customer",
        "sms": "send_sms",
        "storage": "upload_file",
        "identity": "oauth_flow",
        "verification": "create_verification",
    }

    if service in generic_templates:
        default_op = generic_templates[service]
        code = code_templates[service][default_op]
        return {
            "status": "success",
            "service": service,
            "operation": f"{operation} (showing default example: {default_op})",
            "code": code,
            "language": "python",
            "note": f"Specific operation '{operation}' not found. Showing common example.",
        }

    return {"status": "error", "message": f"No code templates available for service '{service}'"}


async def _get_usage_examples(service: str, pattern: str = "") -> dict[str, Any]:
    """Get common usage examples and patterns."""
    examples = {
        "email": {
            "welcome_email": {
                "description": "Send a welcome email when user signs up",
                "code": """# Welcome email pattern
from swap_layer import get_provider

def send_welcome_email(user_email, user_name):
    email = get_provider('email')
    return email.send_email(
        to=[user_email],
        subject=f'Welcome to Our App, {user_name}!',
        html_body=f'''
            <h1>Welcome {user_name}!</h1>
            <p>Thanks for joining our platform.</p>
            <p><a href="https://yourapp.com/get-started">Get Started</a></p>
        ''',
        text_body=f'Welcome {user_name}! Thanks for joining.'
    )""",
            },
            "transactional": {
                "description": "Send transactional emails (receipts, confirmations)",
                "code": """# Transactional email pattern
from swap_layer import get_provider

def send_order_confirmation(order):
    email = get_provider('email')
    return email.send_email(
        to=[order.customer_email],
        subject=f'Order Confirmation #{order.id}',
        html_body=render_template('emails/order_confirmation.html', order=order),
        metadata={'order_id': order.id, 'type': 'order_confirmation'}
    )""",
            },
        },
        "payments": {
            "subscription_flow": {
                "description": "Complete subscription creation flow",
                "code": """# Subscription flow pattern
from swap_layer import get_provider

def create_subscription_for_user(user, plan_price_id):
    payments = get_provider('payments')

    # Create or get customer
    customer = payments.create_customer(
        email=user.email,
        name=user.name,
        metadata={'user_id': str(user.id)}
    )

    # Create subscription
    subscription = payments.create_subscription(
        customer_id=customer['id'],
        price_id=plan_price_id,
        metadata={'user_id': str(user.id)}
    )

    # Save subscription info to your database
    user.stripe_customer_id = customer['id']
    user.stripe_subscription_id = subscription['id']
    user.save()

    return subscription""",
            },
            "one_time_payment": {
                "description": "Process a one-time payment",
                "code": """# One-time payment pattern
from swap_layer import get_provider

def process_payment(amount_cents, customer_email, description):
    payments = get_provider('payments')

    # Create customer
    customer = payments.create_customer(email=customer_email)

    # Create payment intent
    intent = payments.create_payment_intent(
        amount=amount_cents,
        currency='usd',
        customer_id=customer['id'],
        metadata={'description': description}
    )

    return {
        'client_secret': intent['client_secret'],
        'payment_id': intent['id']
    }""",
            },
        },
        "sms": {
            "verification_code": {
                "description": "Send SMS verification code",
                "code": """# SMS verification pattern
from swap_layer import get_provider
import random

def send_verification_code(phone_number):
    # Generate code
    code = random.randint(100000, 999999)

    # Store code in session/cache for verification
    # session['verification_code'] = code

    # Send SMS
    sms = get_provider('sms')
    result = sms.send_sms(
        to=phone_number,
        message=f'Your verification code is: {code}'
    )

    return result""",
            }
        },
        "storage": {
            "user_upload": {
                "description": "Handle user file uploads",
                "code": """# User file upload pattern
from swap_layer import get_provider
from django.core.files.uploadedfile import UploadedFile

def handle_user_upload(uploaded_file: UploadedFile, user_id: int):
    storage = get_provider('storage')

    # Create unique filename
    import uuid
    ext = uploaded_file.name.split('.')[-1]
    filename = f'users/{user_id}/{uuid.uuid4()}.{ext}'

    # Upload to storage
    storage.save(filename, uploaded_file.read())

    # Get URL
    url = storage.url(filename)

    return {'filename': filename, 'url': url}""",
            }
        },
    }

    if service not in examples:
        return {"status": "error", "message": f"No examples available for service '{service}'"}

    if pattern and pattern in examples[service]:
        example = examples[service][pattern]
        return {
            "status": "success",
            "service": service,
            "pattern": pattern,
            "description": example["description"],
            "code": example["code"],
            "language": "python",
        }

    return {
        "status": "success",
        "service": service,
        "patterns": [
            {"name": name, "description": data["description"], "code": data["code"]}
            for name, data in examples[service].items()
        ],
    }


async def _setup_quickstart(
    service: str, provider: str, project_type: str = "existing"
) -> dict[str, Any]:
    """Generate complete quickstart configuration for SwapLayer."""
    quickstart_configs = {
        "email": {
            "sendgrid": {
                "pip_install": "pip install 'SwapLayer[email]'",
                "settings_config": """# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    email={
        'provider': 'sendgrid',
        'sendgrid': {
            'api_key': 'YOUR_SENDGRID_API_KEY_HERE'  # Get from SendGrid dashboard
        }
    }
)

# Optional: Configure default from email
EMAIL_FROM = 'noreply@yourdomain.com'""",
                "env_vars": """# .env file (recommended for production)
SENDGRID_API_KEY=your_actual_api_key_here""",
                "usage_example": """# Example: Send an email
from swap_layer import get_provider

email = get_provider('email')
result = email.send_email(
    to=['user@example.com'],
    subject='Welcome!',
    text_body='Thanks for signing up.',
    html_body='<h1>Thanks for signing up!</h1>'
)""",
                "credentials_instructions": "Get your SendGrid API key from the SendGrid dashboard under Settings > API Keys",
            },
            "mailgun": {
                "pip_install": "pip install 'SwapLayer[email]'",
                "settings_config": """# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    email={
        'provider': 'mailgun',
        'mailgun': {
            'api_key': 'YOUR_MAILGUN_API_KEY_HERE',
            'domain': 'YOUR_MAILGUN_DOMAIN_HERE'  # e.g., 'mg.yourdomain.com'
        }
    }
)""",
                "env_vars": """# .env file (recommended for production)
MAILGUN_API_KEY=your_actual_api_key_here
MAILGUN_DOMAIN=mg.yourdomain.com""",
                "usage_example": """# Example: Send an email
from swap_layer import get_provider

email = get_provider('email')
result = email.send_email(
    to=['user@example.com'],
    subject='Welcome!',
    text_body='Thanks for signing up.'
)""",
                "credentials_instructions": "Get your Mailgun credentials from the Mailgun dashboard under Account > Security",
            },
            "django": {
                "pip_install": "pip install SwapLayer",
                "settings_config": """# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    email={'provider': 'django'}
)

# Configure Django's EMAIL_* settings as normal
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Or your SMTP server
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'YOUR_EMAIL_HERE'
EMAIL_HOST_PASSWORD = 'YOUR_PASSWORD_HERE'""",
                "env_vars": """# .env file
EMAIL_HOST_USER=your.email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password""",
                "usage_example": """# Example: Send an email
from swap_layer import get_provider

email = get_provider('email')
result = email.send_email(
    to=['user@example.com'],
    subject='Welcome!',
    text_body='Thanks for signing up.'
)""",
                "credentials_instructions": "Configure your SMTP server credentials (e.g., Gmail App Password)",
            },
        },
        "payments": {
            "stripe": {
                "pip_install": "pip install 'SwapLayer[stripe]'",
                "settings_config": """# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    payments={
        'provider': 'stripe',
        'stripe': {
            'secret_key': 'YOUR_STRIPE_SECRET_KEY_HERE',  # sk_test_... for testing
            'publishable_key': 'YOUR_STRIPE_PUBLISHABLE_KEY_HERE'  # pk_test_... for testing
        }
    }
)""",
                "env_vars": """# .env file (recommended for production)
STRIPE_SECRET_KEY=sk_test_your_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here""",
                "usage_example": """# Example: Create a customer
from swap_layer import get_provider

payments = get_provider('payments')
customer = payments.create_customer(
    email='customer@example.com',
    name='John Doe'
)
print(f"Customer ID: {customer['id']}")""",
                "credentials_instructions": "Get your Stripe keys from the Stripe Dashboard under Developers > API keys",
            }
        },
        "sms": {
            "twilio": {
                "pip_install": "pip install 'SwapLayer[sms]'",
                "settings_config": """# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    sms={
        'provider': 'twilio',
        'twilio': {
            'account_sid': 'YOUR_TWILIO_ACCOUNT_SID_HERE',
            'auth_token': 'YOUR_TWILIO_AUTH_TOKEN_HERE',
            'from_number': '+15555551234'  # Your Twilio phone number
        }
    }
)""",
                "env_vars": """# .env file (recommended for production)
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_FROM_NUMBER=+15555551234""",
                "usage_example": """# Example: Send SMS
from swap_layer import get_provider

sms = get_provider('sms')
result = sms.send_sms(
    to='+15555555555',
    message='Your verification code is: 123456'
)""",
                "credentials_instructions": "Get your Twilio credentials from the Twilio Console",
            },
            "sns": {
                "pip_install": "pip install 'SwapLayer[aws]'",
                "settings_config": """# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    sms={
        'provider': 'sns',
        'sns': {
            'aws_access_key_id': 'YOUR_AWS_ACCESS_KEY_ID',
            'aws_secret_access_key': 'YOUR_AWS_SECRET_ACCESS_KEY',
            'region_name': 'us-east-1'  # Your AWS region
        }
    }
)""",
                "env_vars": """# .env file (recommended for production)
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_DEFAULT_REGION=us-east-1""",
                "usage_example": """# Example: Send SMS
from swap_layer import get_provider

sms = get_provider('sms')
result = sms.send_sms(
    to='+15555555555',
    message='Your verification code is: 123456'
)""",
                "credentials_instructions": "Get your AWS credentials from the AWS IAM Console",
            },
        },
        "storage": {
            "s3": {
                "pip_install": "pip install 'SwapLayer[aws]'",
                "settings_config": """# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    storage={
        'provider': 's3',
        's3': {
            'bucket_name': 'YOUR_S3_BUCKET_NAME',
            'aws_access_key_id': 'YOUR_AWS_ACCESS_KEY_ID',
            'aws_secret_access_key': 'YOUR_AWS_SECRET_ACCESS_KEY',
            'region_name': 'us-east-1'  # Your AWS region
        }
    }
)""",
                "env_vars": """# .env file (recommended for production)
AWS_S3_BUCKET_NAME=your-bucket-name
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_DEFAULT_REGION=us-east-1""",
                "usage_example": """# Example: Upload a file
from swap_layer import get_provider

storage = get_provider('storage')
with open('myfile.pdf', 'rb') as f:
    storage.save('uploads/myfile.pdf', f.read())

url = storage.url('uploads/myfile.pdf')
print(f"File URL: {url}")""",
                "credentials_instructions": "Create S3 bucket and IAM credentials in the AWS Console",
            },
            "azure": {
                "pip_install": "pip install 'SwapLayer[azure]'",
                "settings_config": """# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    storage={
        'provider': 'azure',
        'azure': {
            'account_name': 'YOUR_AZURE_STORAGE_ACCOUNT',
            'account_key': 'YOUR_AZURE_STORAGE_KEY',
            'container_name': 'YOUR_CONTAINER_NAME'
        }
    }
)""",
                "env_vars": """# .env file (recommended for production)
AZURE_STORAGE_ACCOUNT=your_account_name
AZURE_STORAGE_KEY=your_storage_key
AZURE_CONTAINER_NAME=your-container""",
                "usage_example": """# Example: Upload a file
from swap_layer import get_provider

storage = get_provider('storage')
storage.save('uploads/myfile.pdf', file_content)
url = storage.url('uploads/myfile.pdf')""",
                "credentials_instructions": "Get Azure Storage credentials from the Azure Portal",
            },
            "django": {
                "pip_install": "pip install SwapLayer",
                "settings_config": """# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    storage={'provider': 'django'}
)

# Configure Django storage settings
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'""",
                "env_vars": "# No environment variables needed for local Django storage",
                "usage_example": """# Example: Upload a file
from swap_layer import get_provider

storage = get_provider('storage')
storage.save('uploads/myfile.pdf', file_content)""",
                "credentials_instructions": "No credentials needed - uses local filesystem",
            },
        },
        "identity": {
            "workos": {
                "pip_install": "pip install 'SwapLayer[identity]'",
                "settings_config": """# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    identity={
        'provider': 'workos',
        'workos': {
            'api_key': 'YOUR_WORKOS_API_KEY',
            'client_id': 'YOUR_WORKOS_CLIENT_ID'
        }
    }
)""",
                "env_vars": """# .env file (recommended for production)
WORKOS_API_KEY=your_api_key_here
WORKOS_CLIENT_ID=your_client_id_here""",
                "usage_example": """# Example: OAuth login
from swap_layer import get_provider

identity = get_provider('identity')
auth_url = identity.get_authorization_url(
    request=request,
    redirect_uri='https://yourapp.com/callback',
    state='random_state'
)""",
                "credentials_instructions": "Get WorkOS credentials from the WorkOS Dashboard",
            }
        },
        "verification": {
            "workos": {
                "pip_install": "pip install 'SwapLayer[identity]'",
                "settings_config": """# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    verification={
        'provider': 'workos',
        'workos': {
            'api_key': 'YOUR_WORKOS_API_KEY'
        }
    }
)""",
                "env_vars": """# .env file (recommended for production)
WORKOS_API_KEY=your_api_key_here""",
                "usage_example": """# Example: Create verification session
from swap_layer import get_provider

verification = get_provider('verification')
session = verification.create_verification_session(
    type='identity',
    metadata={'user_id': '123'}
)""",
                "credentials_instructions": "Get WorkOS API key from the WorkOS Dashboard",
            }
        },
    }

    if service not in quickstart_configs:
        return {"status": "error", "message": f"Quickstart not available for service '{service}'"}

    if provider not in quickstart_configs[service]:
        available_providers = list(quickstart_configs[service].keys())
        return {
            "status": "error",
            "message": f"Quickstart not available for provider '{provider}' in service '{service}'",
            "available_providers": available_providers,
        }

    config = quickstart_configs[service][provider]

    setup_steps = [
        f"1. Install SwapLayer with {service} support:",
        f"   {config['pip_install']}",
        "",
        "2. Add configuration to your Django settings.py:",
        config["settings_config"],
        "",
        "3. Set up environment variables (recommended for production):",
        config["env_vars"],
        "",
        "4. Get your credentials:",
        f"   {config['credentials_instructions']}",
        "",
        "5. Start using SwapLayer:",
        config["usage_example"],
    ]

    if project_type == "new":
        setup_steps.insert(0, "0. Create a new Django project if you haven't already:")
        setup_steps.insert(1, "   django-admin startproject myproject")
        setup_steps.insert(2, "   cd myproject")
        setup_steps.insert(3, "")

    return {
        "status": "success",
        "service": service,
        "provider": provider,
        "project_type": project_type,
        "quickstart": "\n".join(setup_steps),
        "pip_install": config["pip_install"],
        "settings_config": config["settings_config"],
        "env_vars": config["env_vars"],
        "usage_example": config["usage_example"],
        "credentials_instructions": config["credentials_instructions"],
    }


# ---------------------------------------------------------------------------
# Onboarding tool implementations (no Django required)
# ---------------------------------------------------------------------------


async def _explain(topic: str) -> dict[str, Any]:
    """Explain a SwapLayer concept."""
    if topic not in _EXPLAIN_TOPICS:
        available = list(_EXPLAIN_TOPICS.keys())
        return {
            "status": "error",
            "message": f"Unknown topic '{topic}'",
            "available_topics": available,
        }

    return {
        "status": "success",
        "topic": topic,
        "content": _EXPLAIN_TOPICS[topic],
        "format": "markdown",
        "related_tools": {
            "overview": ["swaplayer_list_providers", "swaplayer_compare_providers"],
            "philosophy": ["swaplayer_get_migration_guide"],
            "architecture": ["swaplayer_get_provider_info"],
            "installation": ["swaplayer_setup_quickstart"],
            "django-integration": ["swaplayer_setup_quickstart", "swaplayer_generate_code"],
            "security": ["swaplayer_get_config"],
            "providers": ["swaplayer_compare_providers", "swaplayer_setup_quickstart"],
            "faq": ["swaplayer_troubleshoot"],
        }.get(topic, []),
    }


async def _compare_providers(service: str, use_case: str = "") -> dict[str, Any]:
    """Compare providers for a service."""
    if service not in _PROVIDER_COMPARISONS:
        return {"status": "error", "message": f"No comparison data for service '{service}'"}

    comparison = _PROVIDER_COMPARISONS[service]
    result: dict[str, Any] = {
        "status": "success",
        "service": service,
        "summary": comparison["summary"],
        "providers": comparison["providers"],
        "decision_guide": comparison["decision_guide"],
    }

    # If a use case is given, try to highlight the best match
    if use_case:
        use_case_lower = use_case.lower()
        scored: list[tuple[str, int]] = []
        for provider_name, info in comparison["providers"].items():
            score = 0
            text = f"{info['best_for']} {' '.join(info['pros'])} {info.get('recommended_when', '')}".lower()
            for word in use_case_lower.split():
                if word in text:
                    score += 1
            scored.append((provider_name, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        if scored and scored[0][1] > 0:
            result["recommended_for_use_case"] = scored[0][0]
            result["use_case_analysis"] = (
                f"Based on '{use_case}', '{scored[0][0]}' appears to be the best match. "
                f"See its 'recommended_when' field for confirmation."
            )

    return result


async def _troubleshoot(scenario: str, error_message: str = "") -> dict[str, Any]:
    """Diagnose a SwapLayer configuration issue."""
    if scenario not in _TROUBLESHOOT_SCENARIOS:
        available = list(_TROUBLESHOOT_SCENARIOS.keys())
        return {
            "status": "error",
            "message": f"Unknown scenario '{scenario}'",
            "available_scenarios": available,
        }

    info = _TROUBLESHOOT_SCENARIOS[scenario]
    result: dict[str, Any] = {
        "status": "success",
        "scenario": scenario,
        "symptoms": info["symptoms"],
        "cause": info["cause"],
        "solution": info["solution"],
    }

    if error_message:
        result["error_message_provided"] = error_message
        # Try to match the error to a known symptom pattern
        for symptom in info["symptoms"]:
            if any(word in error_message for word in symptom.split()):
                result["symptom_matched"] = symptom
                break

    return result


async def _get_migration_guide(
    service: str, from_provider: str, to_provider: str
) -> dict[str, Any]:
    """Generate a provider migration guide."""
    valid_providers = {
        "email": ["django", "smtp", "sendgrid", "mailgun", "ses"],
        "payments": ["stripe", "paypal", "square"],
        "sms": ["twilio", "sns"],
        "storage": ["local", "django", "s3", "azure", "gcs"],
        "identity": ["workos", "auth0"],
        "verification": ["stripe", "persona"],
    }

    if service not in valid_providers:
        return {"status": "error", "message": f"Unknown service: {service}"}

    known = valid_providers[service]
    warnings = []
    if from_provider not in known:
        warnings.append(
            f"'{from_provider}' is not a recognised provider for {service}. Known: {known}"
        )
    if to_provider not in known:
        warnings.append(
            f"'{to_provider}' is not a recognised provider for {service}. Known: {known}"
        )

    # Data migration notes by service
    data_notes: dict[str, str] = {
        "payments": (
            "Customer IDs and subscription IDs are provider-specific. "
            "You will need to migrate customers and subscriptions to the new provider, "
            "or maintain both providers during a transition period. "
            "This is the ONE case where application code may need updating: "
            "any stored customer_id / subscription_id values in your database are "
            "provider-specific and must be re-mapped."
        ),
        "email": (
            "No data migration required. "
            "Suppression lists (unsubscribes) are provider-specific — "
            "export them from your current provider and import into the new one."
        ),
        "sms": (
            "No data migration required. "
            "Opt-out lists are provider-specific — ensure you honour existing opt-outs "
            "by importing them into the new provider before sending."
        ),
        "storage": (
            "Files are stored in the old provider's bucket/container. "
            "You must either: (a) copy all files to the new provider, "
            "or (b) run both providers simultaneously during a migration window. "
            "File URLs stored in your database will change."
        ),
        "identity": (
            "User sessions managed by the old provider will be invalidated. "
            "Users will need to log in again after migration. "
            "Directory sync / SCIM data must be re-configured with the new provider."
        ),
        "verification": (
            "Completed verification records are stored in your database via SwapLayer's models. "
            "In-progress verification sessions will be invalidated. "
            "No action needed for already-completed verifications."
        ),
    }

    steps = [
        f"## Migration Guide: {service} from '{from_provider}' to '{to_provider}'",
        "",
        "### Step 1 — Install the new provider's package (if needed)",
        f"   Use `swaplayer_setup_quickstart(service='{service}', provider='{to_provider}')` "
        "to get the exact pip install command.",
        "",
        "### Step 2 — Get credentials for the new provider",
        f"   Sign up / log in to the {to_provider} dashboard and obtain your API keys.",
        "",
        "### Step 3 — Add new credentials to your environment",
        "   Add the new provider's environment variables to your .env file.",
        "   Keep the OLD provider's variables until migration is complete.",
        "",
        "### Step 4 — Update SWAPLAYER settings",
        f"   Change `'provider': '{from_provider}'` to `'provider': '{to_provider}'` "
        "and add the new provider's credential block:",
        "",
        "   ```python",
        "   # settings.py — BEFORE",
        "   SWAPLAYER = SwapLayerSettings(",
        f"       {service}={{",
        f"           'provider': '{from_provider}',",
        f"           '{from_provider}': {{ ... old credentials ... }}",
        "       }",
        "   )",
        "",
        "   # settings.py — AFTER",
        "   SWAPLAYER = SwapLayerSettings(",
        f"       {service}={{",
        f"           'provider': '{to_provider}',",
        f"           '{to_provider}': {{ ... new credentials ... }}",
        "       }",
        "   )",
        "   ```",
        "",
        "### Step 5 — Application code changes",
        "   NONE. Your application code uses `get_provider('" + service + "')` and calls",
        "   the same methods regardless of provider. Zero lines of application code change.",
        "",
        "### Step 6 — Test",
        "   Use `swaplayer_send_test_email` / `swaplayer_check_storage` / etc. "
        "to verify the new provider works.",
        "",
        "### Step 7 — Data migration",
        f"   {data_notes.get(service, 'No data migration required.')}",
        "",
        "### Step 8 — Remove old provider credentials",
        "   Once migration is verified, remove the old provider's environment variables",
        "   and credential block from settings.",
    ]

    return {
        "status": "success",
        "service": service,
        "from_provider": from_provider,
        "to_provider": to_provider,
        "application_code_changes": "none",
        "data_migration_note": data_notes.get(service, "No data migration required."),
        "guide": "\n".join(steps),
        "warnings": warnings,
    }
