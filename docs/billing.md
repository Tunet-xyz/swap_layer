# Payment Infrastructure

This module provides an abstraction layer for payment and subscription providers, allowing the application to switch between Stripe, PayPal, and Square without modifying business logic.

## Subdomain Architecture

The payment infrastructure is organized into logical subdomains, each handling a specific area of payment functionality:

### 1. **Customers** (`swap_layer.payments.customers`)
Handles customer management operations:
- Create, retrieve, update, and delete customers

### 2. **Subscriptions** (`swap_layer.payments.subscriptions`)
Manages recurring subscription lifecycle:
- Create, retrieve, update, cancel, and list subscriptions

### 3. **Payment Intents** (`swap_layer.payments.payment_intents`)
Handles payment processing and related operations:
- Payment methods (attach, detach, list, set default)
- One-time payments (payment intents)
- Checkout sessions
- Invoices
- Webhook verification

### 4. **Products** (`swap_layer.payments.products`)
Product catalog and pricing management:
- Create and list products and prices through the common billing interface
- Discover Stripe meters, products, prices, and Entitlements features
- Update mutable Stripe prices or replace immutable prices with explicit archival controls
- Attach and detach Stripe Entitlements features from products
- [Documentation](./products/README.md)

## Architecture

The payment infrastructure follows a subdomain-based pattern with adapter composition:

```
swap_layer/payments/
â”œâ”€â”€ __init__.py
â”œâ”€â”€ apps.py                      # Django AppConfig
â”œâ”€â”€ adapter.py                   # Main adapter (composes subdomain adapters)
â”œâ”€â”€ factory.py                   # Provider selection factory
â”œâ”€â”€ customers/                   # Customer management subdomain
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ adapter.py              # CustomerAdapter interface
â”‚   â””â”€â”€ README.md
â”œâ”€â”€ subscriptions/              # Subscription management subdomain
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ adapter.py              # SubscriptionAdapter interface
â”‚   â””â”€â”€ README.md
â”œâ”€â”€ payment_intents/            # Payment processing subdomain
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ adapter.py              # PaymentAdapter interface
â”‚   â””â”€â”€ README.md
â”œâ”€â”€ products/                   # Product/pricing subdomain (placeholder)
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ adapter.py              # ProductAdapter interface
â”‚   â””â”€â”€ README.md
â””â”€â”€ providers/                  # Provider implementations
    â”œâ”€â”€ __init__.py
    â””â”€â”€ stripe.py               # Stripe implementation
```

## Design Pattern

### 1. Subdomain Adapters

Each subdomain defines its own adapter interface:

- **CustomerAdapter** (`customers/adapter.py`): Customer management operations
- **SubscriptionAdapter** (`subscriptions/adapter.py`): Subscription lifecycle operations
- **PaymentAdapter** (`payment_intents/adapter.py`): Payment processing operations
- **ProductAdapter** (`products/adapter.py`): Product and pricing management (placeholder)

### 2. Composition via Multiple Inheritance

The main `PaymentProviderAdapter` class composes all subdomain adapters:

```python
class PaymentProviderAdapter(ABC, CustomerAdapter, SubscriptionAdapter, 
                            PaymentAdapter, ProductAdapter):
    """
    Unified payment provider interface that includes all subdomain operations.
    Provider implementations inherit from this class and implement all methods.
    """
```

### 3. Benefits of Subdomain Organization

1. **Modularity**: Each subdomain can be understood and modified independently
2. **Clear Responsibilities**: Logical grouping of related operations
3. **Easier Navigation**: Developers can quickly find relevant functionality
4. **Documentation**: Each subdomain has its own focused documentation
5. **Future Extensibility**: New subdomains can be added without affecting existing ones
6. **Backward Compatibility**: Existing code continues to work unchanged

### 4. Abstract Base Class (`adapter.py`)

The `PaymentProviderAdapter` defines the complete interface by composing subdomain adapters:

- **Customer Management** (via CustomerAdapter): Create, retrieve, update, delete customers
- **Subscription Management** (via SubscriptionAdapter): Create, retrieve, update, cancel, list subscriptions
- **Payment Methods** (via PaymentAdapter): Attach, detach, list, set default payment methods
- **One-time Payments** (via PaymentAdapter): Create, confirm, retrieve payment intents
- **Checkout Sessions** (via PaymentAdapter): Create hosted checkout pages, retrieve session details
- **Invoices** (via PaymentAdapter): Retrieve and list invoices
- **Webhooks** (via PaymentAdapter): Verify webhook signatures and parse events
- **Product Management** (via ProductAdapter): Manage products and pricing (placeholder)

### 5. Provider Implementations (`providers/`)

Each provider (e.g., Stripe, PayPal) implements the `PaymentProviderAdapter` interface:

```python
class StripePaymentProvider(PaymentProviderAdapter):
    def create_customer(self, email, name=None, metadata=None):
        # Stripe-specific implementation
        customer = stripe.Customer.create(email=email, name=name)
        return normalized_data
```

### 6. Factory Function (`factory.py`)

The factory function returns the appropriate provider based on Django settings:

```python
from swap_layer.payments.factory import get_payment_provider

# Get the configured provider (defaults to Stripe)
provider = get_payment_provider()

# Use the provider
customer = provider.create_customer(
    email='user@example.com',
    name='John Doe'
)
```

## Configuration

Add to your Django `settings.py`:

```python
# Payment Provider Selection
PAYMENT_PROVIDER = 'stripe'  # Options: 'stripe', 'paypal', 'square'

# Stripe Configuration (if using Stripe)
STRIPE_SECRET_KEY = 'sk_test_...'  # From Stripe Dashboard
STRIPE_PUBLIC_KEY = 'pk_test_...'
STRIPE_WEBHOOK_SECRET = 'whsec_...'  # For webhook validation
```

**Security Best Practice:** Use Django's environment variable integration or a secrets manager:

```python
import os
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
```


### PayPal Configuration

Use PayPal when you want an alternative provider for products, plans, subscriptions, checkout orders, invoicing, refunds, and webhook verification:

```python
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    billing={
        "provider": "paypal",
        "paypal": {
            "client_id": os.environ["PAYPAL_CLIENT_ID"],
            "client_secret": os.environ["PAYPAL_CLIENT_SECRET"],
            "webhook_id": os.environ.get("PAYPAL_WEBHOOK_ID"),
            "sandbox": True,
        },
    }
)
```

Legacy Django settings are also supported:

```python
PAYMENT_PROVIDER = "paypal"
PAYPAL_CLIENT_ID = os.environ["PAYPAL_CLIENT_ID"]
PAYPAL_CLIENT_SECRET = os.environ["PAYPAL_CLIENT_SECRET"]
PAYPAL_WEBHOOK_ID = os.environ.get("PAYPAL_WEBHOOK_ID")
PAYPAL_SANDBOX = True
```

PayPal does not have direct equivalents for Stripe Billing Meters, Stripe coupons/promotion codes, Stripe tax-rate objects, or Stripe's hosted customer billing portal. SwapLayer raises `PaymentValidationError` for those methods when the PayPal provider is selected, so unsupported capabilities fail clearly instead of pretending to work.
Add to INSTALLED_APPS:

```python
INSTALLED_APPS = [
    # ...
    'swap_layer.payments.apps.PaymentsConfig',
    # ...
]
```

## Usage Examples

### Customer Management

```python
from swap_layer.payments.factory import get_payment_provider

provider = get_payment_provider()

# Create a customer
customer = provider.create_customer(
    email='user@example.com',
    name='John Doe',
    metadata={'user_id': '123'}
)
print(customer['id'])  # Provider-specific customer ID

# Retrieve customer
customer = provider.get_customer(customer_id='cus_123')

# Update customer
updated = provider.update_customer(
    customer_id='cus_123',
    email='newemail@example.com'
)

# Delete customer
provider.delete_customer(customer_id='cus_123')
```

### Subscription Management

```python
# Create subscription
subscription = provider.create_subscription(
    customer_id='cus_123',
    price_id='price_abc',
    trial_period_days=14,
    metadata={'plan': 'pro'}
)

# Get subscription
subscription = provider.get_subscription(subscription_id='sub_123')
print(subscription['status'])  # active, canceled, etc.

# Update subscription (change plan)
updated = provider.update_subscription(
    subscription_id='sub_123',
    price_id='price_xyz'  # New plan
)

# Cancel subscription
canceled = provider.cancel_subscription(
    subscription_id='sub_123',
    at_period_end=True  # Cancel at end of billing period
)

# List subscriptions
subscriptions = provider.list_subscriptions(
    customer_id='cus_123',
    status='active'
)
```

### Payment Methods

```python
# Attach payment method
payment_method = provider.attach_payment_method(
    customer_id='cus_123',
    payment_method_id='pm_123'
)

# List payment methods
methods = provider.list_payment_methods(
    customer_id='cus_123',
    method_type='card'
)

# Set default payment method
provider.set_default_payment_method(
    customer_id='cus_123',
    payment_method_id='pm_123'
)

# Detach payment method
provider.detach_payment_method(payment_method_id='pm_123')
```

### One-time Payments

```python
from decimal import Decimal

# Create payment intent
payment_intent = provider.create_payment_intent(
    amount=Decimal('500'),  # Â£5.00 (in pence)
    currency='gbp',
    customer_id='cus_123',
    metadata={'order_id': 'ord_456'}
)
client_secret = payment_intent['client_secret']

# Confirm payment intent
confirmed = provider.confirm_payment_intent(
    payment_intent_id='pi_123',
    payment_method_id='pm_123'
)

# Get payment intent
payment = provider.get_payment_intent(payment_intent_id='pi_123')
```

### Checkout Sessions

```python
# Create checkout session for subscription
session = provider.create_checkout_session(
    customer_id='cus_123',
    price_id='price_abc',
    success_url='https://example.com/success',
    cancel_url='https://example.com/cancel',
    mode='subscription'
)
checkout_url = session['url']  # Redirect user here

# Create checkout session for one-time payment
session = provider.create_checkout_session(
    price_id='price_one_time',
    success_url='https://example.com/success',
    cancel_url='https://example.com/cancel',
    mode='payment'
)

# Get checkout session
session = provider.get_checkout_session(session_id='cs_123')
```

### Webhooks

SwapLayer also exposes provider-neutral webhook endpoint lifecycle operations. Stripe
creation returns the signing secret once; move that value directly to an approved
secret manager and never log or persist the creation response:

```python
endpoint = provider.create_webhook_endpoint(
    "https://api.example.com/webhooks/stripe",
    ["checkout.session.completed", "customer.subscription.updated"],
    metadata={"tunet_product_id": "example"},
)
secret_manager.add_version("example-stripe-webhook-secret", endpoint.pop("secret"))
```

`list_webhook_endpoints()` and `get_webhook_endpoint()` deliberately omit signing
secrets. Updating an endpoint does not rotate its secret; deletion is always an
explicit call.

```python
# In your webhook view
def payment_webhook(request):
    payload = request.body
    signature = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    
    try:
        event = provider.verify_webhook_signature(
            payload=payload,
            signature=signature,
            webhook_secret=webhook_secret
        )
        
        # Handle event
        if event['type'] == 'customer.subscription.created':
            subscription = event['data']
            # Process new subscription
        elif event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']
            # Process successful payment
            
        return HttpResponse(status=200)
    except ValueError as e:
        return HttpResponse(status=400)
```

## Normalized Data Format

All provider implementations return data in a standardized format:

### Customer
```python
{
    'id': 'cus_123',
    'email': 'user@example.com',
    'name': 'John Doe',
    'created': 1234567890,
    'metadata': {'user_id': '123'}
}
```

### Subscription
```python
{
    'id': 'sub_123',
    'customer_id': 'cus_123',
    'status': 'active',
    'current_period_start': 1234567890,
    'current_period_end': 1234567890,
    'cancel_at_period_end': False,
    'items': [
        {
            'id': 'si_123',
            'price_id': 'price_abc',
            'quantity': 1
        }
    ]
}
```

### Payment Intent
```python
{
    'id': 'pi_123',
    'amount': 500,
    'currency': 'gbp',
    'status': 'succeeded',
    'client_secret': 'pi_123_secret_abc',
    'metadata': {}
}
```

## Adding a New Provider

Stripe, PayPal, and Square are included. To add another payment provider:

1. Create a new file in `providers/`.
2. Implement the `PaymentProviderAdapter` interface.
3. Register the provider in `factory.py` and `providers/__init__.py`.
4. Add `SwapLayerSettings` validation, documentation, and provider-specific tests.
## Benefits

1. **Provider Independence**: Switch payment providers without changing business logic
2. **Consistent Interface**: All providers expose the same methods with normalized data
3. **Easy Testing**: Mock the adapter interface for unit tests
4. **Gradual Migration**: Test new providers alongside existing ones
5. **Multi-provider Support**: Support multiple providers simultaneously if needed
6. **Type Safety**: Abstract methods ensure all providers implement required functionality

## Comparison with Auth Abstraction

This payment abstraction follows the same architectural pattern as the authentication layer:

| Component | Auth | Payments |
|-----------|------|----------|
| Base Class | `AuthProviderAdapter` | `PaymentProviderAdapter` |
| Factory | `get_identity_client()` | `get_payment_provider()` |
| Providers | Auth0, WorkOS | Stripe, PayPal, Square |
| Location | `swap_layer/identity/platform/` | `swap_layer/payments/` |
| Config Key | `IDENTITY_PROVIDER` | `PAYMENT_PROVIDER` |

## Migration Guide

If you have existing Stripe code, migrate it gradually:

**Before:**
```python
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
customer = stripe.Customer.create(email='user@example.com')
```

**After:**
```python
from swap_layer.payments.factory import get_payment_provider
provider = get_payment_provider()
customer = provider.create_customer(email='user@example.com')
```

## Testing

```python
from unittest.mock import Mock
from swap_layer.payments.adapter import PaymentProviderAdapter

def test_subscription_creation():
    # Mock the provider
    mock_provider = Mock(spec=PaymentProviderAdapter)
    mock_provider.create_subscription.return_value = {
        'id': 'sub_test',
        'status': 'active'
    }
    
    # Test your business logic
    result = mock_provider.create_subscription(
        customer_id='cus_test',
        price_id='price_test'
    )
    
    assert result['status'] == 'active'
```

## Future Enhancements

- Add support for Braintree
- Add caching layer for frequently accessed data
- Add support for multiple concurrent providers
- Expand machine-readable provider capability discovery
## Expanded Stripe Billing Surface

The Stripe provider exposes the common application billing flows directly through the payment provider interface:

```python
from swap_layer.billing.factory import get_payment_provider

billing = get_payment_provider()

product = billing.create_product("Pro", description="Team plan")
price = billing.create_price(
    product_id=product["id"],
    amount=2500,
    currency="usd",
    recurring={"interval": "month"},
    lookup_key="pro_monthly",
)

session = billing.create_checkout_session(
    customer_id="cus_123",
    price_id=price["id"],
    success_url="https://app.example.com/billing/success",
    cancel_url="https://app.example.com/billing/cancel",
    allow_promotion_codes=True,
    automatic_tax={"enabled": True},
)
```

### Metered usage

For usage-based billing with Stripe Billing Meters:

```python
meter = billing.create_meter(
    display_name="Tokens",
    event_name="tokens_used",
)

billing.record_usage(
    event_name="tokens_used",
    customer_id="cus_123",
    value=42,
    identifier="usage-event-123",
    idempotency_key="usage-event-123",
)
```

High-throughput usage ingestion can use Stripe API v2 meter event sessions and streams:

```python
session = billing.create_meter_event_session()
billing.create_meter_event_stream(
    events=[{"event_name": "tokens_used", "payload": {"stripe_customer_id": "cus_123", "value": "42"}}],
    authentication_token=session["authentication_token"],
)
```

### Customer billing operations

The provider also supports customer portal sessions, refunds, coupons, promotion codes, tax rates, invoice create/finalize/pay/void actions, subscription pause/resume, and webhook dispatch:

```python
portal = billing.create_billing_portal_session("cus_123", return_url="https://app.example.com/account")
refund = billing.create_refund(payment_intent_id="pi_123", amount=500)
coupon = billing.create_coupon(percent_off=20, name="Launch discount")
promo = billing.create_promotion_code(coupon_id=coupon["id"], code="LAUNCH20")
tax_rate = billing.create_tax_rate("VAT", 20, country="GB")

verified = billing.verify_webhook_signature(payload, signature)
result = billing.dispatch_webhook_event(
    verified,
    {"invoice.payment_succeeded": handle_invoice_paid},
    processed_event_ids=seen_event_ids,
)
```
