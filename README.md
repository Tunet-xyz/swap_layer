# SwapLayer
### The Anti-Vendor-Lock-in Framework for Django

**One Interface. Any Provider. Zero Rewrites.**

---

## The Origin Story: "Never Again"

2025 was the hardest year of my professional life. I was two weeks away from onboarding a major client when my database provider, FaunaDB, effectively imploded for my use case. 

My entire codebase was tightly coupled to their specific SDKs. I didn't just have a "database problem"; I had a "rewrite the whole application" problem. I lost the client. I lost months of work. I lost sleep.

I swore: **Never Again.**

I realized that "Vendor Lock-in" isn't just a buzzword—it's a business risk. If you import `stripe` or `boto3` or `twilio` directly into your business logic, you are handing the keys of your architecture to a third party.

I built **SwapLayer** to ensure that no external vendor failure could ever sink my platform again.

---

## What is SwapLayer?

SwapLayer is a **unified infrastructure layer** for Django applications. 

Instead of stitching together 5 different libraries with 5 different patterns, you install **one package** that provides a consistent, "Adapter-based" interface for all your external integrations.

It is designed to be the **"Firewall"** between your clean business logic and the messy world of third-party APIs.

### The "Single Package" Philosophy
We believe you shouldn't have to hunt down a dozen micro-libraries to build a standard SaaS. SwapLayer is a cohesive suite:

*   **One Import:** `from swap_layer import get_provider`
*   **One Pattern:** Consistent `Adapter` interfaces for Auth, Payments, Storage, Email, and SMS.
*   **One Config:** Centralized settings.
*   **Zero Lock-in:** Swap underlying vendors by changing ONE line of config.

---

## Architecture: The "Meta-Framework"

We don't reinvent the wheel. We make the wheel interchangeable.

SwapLayer uses a **Wrapper Pattern** to leverage the best existing tools while enforcing a unified API.

| Domain | Strategy | Underlying Tech | The Value |
| :--- | :--- | :--- | :--- |
| **Storage** | **Wrapper** | `django-storages` | Unified interface for S3, Azure, GCloud, Local. |
| **Email** | **Wrapper** | `django-anymail` | Unified interface for SendGrid, Mailgun, SES. |
| **Payments** | **Custom** | Stripe / PayPal | **The Missing Link.** A unified Payment Adapter that Django lacks. |
| **Identity** | **Custom** | Auth0 / WorkOS | Lightweight OIDC/OAuth abstraction. |
| **SMS** | **Custom** | Twilio / SNS | Simple, consistent messaging interface. |

---

## Usage Example

### 1. The Old Way (The "Risk" Way)
Tightly coupled code that breaks if you switch vendors.

```python
# views.py
import stripe
import boto3

def signup(request):
    # Direct dependency on Stripe!
    customer = stripe.Customer.create(email=request.user.email)
    
    # Direct dependency on AWS!
    s3 = boto3.client('s3')
    s3.upload_file(...)
```

### 2. The SwapLayer Way (The "Safe" Way)
Vendor-agnostic code. The "Provider" is injected based on settings.

```python
# views.py
from infrastructure.payments.factory import get_payment_provider
from infrastructure.storage.factory import get_storage_provider

def signup(request):
    # Code doesn't know if it's Stripe or PayPal
    payments = get_payment_provider()
    customer = payments.create_customer(email=request.user.email)
    
    # Code doesn't know if it's S3 or Azure
    storage = get_storage_provider()
    storage.upload_file(...)
```

---

## Installation

```bash
# Install the core framework
pip install swap-layer

# Install with specific provider support (Optional Dependencies)
pip install swap-layer[stripe,aws,sendgrid]
```

## Configuration

```python
# settings.py

# Switch providers instantly. No code changes required.
PAYMENT_PROVIDER = 'stripe'  # or 'paypal'
STORAGE_PROVIDER = 'django'  # uses django-storages backend
EMAIL_PROVIDER   = 'django'  # uses django-anymail backend
```

---

## Status
*   **Storage:** ✅ Production Ready (Wraps `django-storages`)
*   **Email:** ✅ Production Ready (Wraps `django-anymail`)
*   **Payments:** 🚧 Beta (Stripe implemented, PayPal planned)
*   **Identity:** 🚧 Beta (Auth0 implemented)

## License
MIT. Because safety should be free.
