# Payment Infrastructure

This module provides an abstraction layer for payment and subscription providers, allowing the application to switch between different payment services (Stripe, PayPal, Square, etc.) without modifying business logic.

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
Product catalog and pricing management (placeholder for future implementation):
- Product management
- Pricing configuration
- [Documentation](./products/README.md)

## Architecture

The payment infrastructure follows a subdomain-based pattern with adapter composition:

```
swap_layer/payments/
├── __init__.py
├── apps.py                      # Django AppConfig
├── adapter.py                   # Main adapter (composes subdomain adapters)
├── factory.py                   # Provider selection factory
├── customers/                   # Customer management subdomain
│   ├── __init__.py
│   ├── adapter.py              # CustomerAdapter interface
│   └── README.md
├── subscriptions/              # Subscription management subdomain
│   ├── __init__.py
│   ├── adapter.py              # SubscriptionAdapter interface
│   └── README.md
├── payment_intents/            # Payment processing subdomain
│   ├── __init__.py
│   ├── adapter.py              # PaymentAdapter interface
│   └── README.md
├── products/                   # Product/pricing subdomain (placeholder)
│   ├── __init__.py
│   ├── adapter.py              # ProductAdapter interface
│   └── README.md
└── providers/                  # Provider implementations
    ├── __init__.py
    └── stripe.py               # Stripe implementation
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
PAYMENT_PROVIDER = 'stripe'  # Options: 'stripe', 'paypal', 'square', etc.

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

Add to `INSTALLED_APPS`:

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
    amount=Decimal('500'),  # £5.00 (in pence)
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

To add a new payment provider (e.g., PayPal):

1. Create a new file `providers/paypal.py`
2. Implement the `PaymentProviderAdapter` interface:

```python
from swap_layer.payments.adapter import PaymentProviderAdapter

class PayPalPaymentProvider(PaymentProviderAdapter):
    def __init__(self):
        # Initialize PayPal SDK
        pass
    
    def create_customer(self, email, name=None, metadata=None):
        # PayPal-specific implementation
        pass
    
    # Implement all other required methods...
```

3. Register the provider in `factory.py`:

```python
def get_payment_provider() -> PaymentProviderAdapter:
    provider = getattr(settings, 'PAYMENT_PROVIDER', 'stripe')
    
    if provider == 'stripe':
        return StripePaymentProvider()
    elif provider == 'paypal':
        from .providers.paypal import PayPalPaymentProvider
        return PayPalPaymentProvider()
    else:
        raise ValueError(f"Unknown Payment Provider: {provider}")
```

4. Update settings:

```python
PAYMENT_PROVIDER = 'paypal'
PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID')
PAYPAL_SECRET = os.environ.get('PAYPAL_SECRET')
```

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
| Providers | Auth0, WorkOS | Stripe (+ future providers) |
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

- Add support for PayPal
- Add support for Square
- Add support for Braintree
- Implement provider-agnostic webhook routing
- Add caching layer for frequently accessed data
- Add support for multiple concurrent providers
- Add provider capability detection (e.g., some providers may not support certain features)
