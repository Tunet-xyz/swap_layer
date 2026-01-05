# Payment Abstraction Layer - Architecture Comparison

This document compares the payment abstraction layer with the existing authentication abstraction to demonstrate the consistent architectural pattern.

## Overview

Both the authentication and payment systems follow the **Provider Adapter Pattern**, allowing the application to switch between different service providers without modifying business logic.

## Side-by-Side Comparison

### Directory Structure

```
Authentication:                          Payments:
infrastructure/identity/platform/        infrastructure/payments/
├── __init__.py                         ├── __init__.py
├── adapter.py                          ├── adapter.py
├── factory.py                          ├── factory.py
├── apps.py                             ├── apps.py
└── vendors/                            └── providers/
    ├── auth0/                              ├── __init__.py
    │   └── client.py                       └── stripe.py
    └── workos/
        └── client.py
```

### Abstract Base Classes

#### Authentication Adapter
```python
# infrastructure/identity/platform/adapter.py
from abc import ABC, abstractmethod

class AuthProviderAdapter(ABC):
    @abstractmethod
    def get_authorization_url(self, request, redirect_uri, state=None):
        """Generate URL to redirect user for login."""
        pass

    @abstractmethod
    def exchange_code_for_user(self, request, code):
        """Exchange authorization code for user details."""
        pass

    @abstractmethod
    def get_logout_url(self, request, return_to):
        """Generate URL to redirect user for logout."""
        pass
```

#### Payment Adapter
```python
# infrastructure/payments/adapter.py
from abc import ABC, abstractmethod

class PaymentProviderAdapter(ABC):
    @abstractmethod
    def create_customer(self, email, name=None, metadata=None):
        """Create a customer in the payment provider."""
        pass

    @abstractmethod
    def create_subscription(self, customer_id, price_id, ...):
        """Create a subscription for a customer."""
        pass

    @abstractmethod
    def verify_webhook_signature(self, payload, signature, secret):
        """Verify and parse a webhook payload."""
        pass
    
    # ... 18 more methods for complete payment/subscription management
```

**Key Difference**: Payment adapter has more methods (21 vs 3) due to the complexity of payment operations, but follows the same abstraction principle.

### Factory Functions

#### Authentication Factory
```python
# infrastructure/identity/platform/factory.py
from django.conf import settings

def get_identity_client(app_name='default'):
    provider = getattr(settings, 'IDENTITY_PROVIDER', 'workos')
    
    if provider == 'workos':
        return WorkOSClient(app_name=app_name)
    elif provider == 'auth0':
        return Auth0Client(app_name=app_name)
    else:
        raise ValueError(f"Unknown Identity Provider: {provider}")
```

#### Payment Factory
```python
# infrastructure/payments/factory.py
from django.conf import settings

def get_payment_provider():
    provider = getattr(settings, 'PAYMENT_PROVIDER', 'stripe')
    
    if provider == 'stripe':
        return StripePaymentProvider()
    # elif provider == 'paypal':
    #     return PayPalPaymentProvider()
    else:
        raise ValueError(f"Unknown Payment Provider: {provider}")
```

**Pattern**: Same factory pattern, returns appropriate provider based on configuration.

### Provider Implementations

#### WorkOS Auth Provider
```python
# infrastructure/identity/platform/vendors/workos/client.py
class WorkOSClient(AuthProviderAdapter):
    def __init__(self, app_name='default'):
        self.config = settings.WORKOS_APPS.get(app_name)
        workos.api_key = self.config['api_key']
        self.client = workos.client

    def get_authorization_url(self, request, redirect_uri, state=None):
        return self.client.user_management.get_authorization_url(
            provider=UserManagementProviderType.AuthKit,
            redirect_uri=redirect_uri,
            state=state
        )
    
    def exchange_code_for_user(self, request, code):
        response = self.client.user_management.authenticate_with_code(...)
        return {
            'id': response.user.id,
            'email': response.user.email,
            # ... normalized user data
        }
```

#### Stripe Payment Provider
```python
# infrastructure/payments/providers/stripe.py
class StripePaymentProvider(PaymentProviderAdapter):
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_customer(self, email, name=None, metadata=None):
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata=metadata
        )
        return {
            'id': customer.id,
            'email': customer.email,
            # ... normalized customer data
        }
    
    def create_subscription(self, customer_id, price_id, ...):
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{'price': price_id}],
            ...
        )
        return self._normalize_subscription(subscription)
```

**Pattern**: Both normalize provider-specific responses into consistent formats.

### Configuration

#### Authentication Configuration
```python
# codedx/settings.py

# Identity Provider Selection
IDENTITY_PROVIDER = 'workos'  # or 'auth0'

# WorkOS Configuration
WORKOS_APPS = {
    'default': {
        'api_key': os.environ.get('WORKOS_API_KEY'),
        'client_id': os.environ.get('WORKOS_CLIENT_ID'),
        'cookie_password': os.environ.get('WORKOS_COOKIE_PASSWORD')
    }
}

# Auth0 Configuration
AUTH0_APPS = {
    'developer': {
        'client_id': os.environ.get('AUTH0_CLIENT_ID'),
        'client_secret': os.environ.get('AUTH0_CLIENT_SECRET')
    }
}
```

#### Payment Configuration
```python
# codedx/settings.py

# Payment Provider Selection
PAYMENT_PROVIDER = 'stripe'  # or 'paypal', 'square', etc.

# Stripe Configuration
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

# Future: PayPal Configuration
# PAYPAL_CLIENT_ID = os.environ.get('PAYPAL_CLIENT_ID')
# PAYPAL_SECRET = os.environ.get('PAYPAL_SECRET')
```

### Usage in Application Code

#### Using Authentication Abstraction
```python
from infrastructure.identity.platform.factory import get_identity_client

def login_view(request):
    client = get_identity_client(app_name='default')
    
    # Provider-agnostic login
    auth_url = client.get_authorization_url(
        request=request,
        redirect_uri='https://example.com/callback',
        state='random_state'
    )
    
    return redirect(auth_url)

def callback_view(request):
    client = get_identity_client(app_name='default')
    
    # Provider-agnostic user data retrieval
    user_data = client.exchange_code_for_user(
        request=request,
        code=request.GET.get('code')
    )
    
    # user_data is normalized regardless of provider
    create_or_update_user(user_data)
```

#### Using Payment Abstraction
```python
from infrastructure.payments.factory import get_payment_provider

def create_subscription_view(request):
    provider = get_payment_provider()
    
    # Provider-agnostic customer creation
    customer = provider.create_customer(
        email=request.user.email,
        name=request.user.get_full_name(),
        metadata={'user_id': str(request.user.id)}
    )
    
    # Provider-agnostic subscription creation
    subscription = provider.create_subscription(
        customer_id=customer['id'],
        price_id='price_abc123',
        trial_period_days=14
    )
    
    # Data is normalized regardless of provider
    save_subscription(subscription)

def webhook_view(request):
    provider = get_payment_provider()
    
    # Provider-agnostic webhook handling
    event = provider.verify_webhook_signature(
        payload=request.body,
        signature=request.META.get('HTTP_STRIPE_SIGNATURE'),
        webhook_secret=settings.STRIPE_WEBHOOK_SECRET
    )
    
    process_event(event)
```

## Architectural Benefits

Both abstractions provide the same benefits:

### 1. Provider Independence
- Switch providers by changing one configuration setting
- No changes to business logic required
- Gradual migration path (can test new provider alongside old)

### 2. Consistent Interface
- All providers expose the same methods
- Normalized data formats across providers
- Predictable behavior regardless of underlying service

### 3. Easy Testing
```python
from unittest.mock import Mock

# Mock auth provider
mock_auth = Mock(spec=AuthProviderAdapter)
mock_auth.exchange_code_for_user.return_value = {'id': '123', 'email': 'test@example.com'}

# Mock payment provider
mock_payment = Mock(spec=PaymentProviderAdapter)
mock_payment.create_customer.return_value = {'id': 'cus_123', 'email': 'test@example.com'}
```

### 4. Clear Separation of Concerns
- Infrastructure layer: Provider communication
- Service layer: Business logic
- View layer: HTTP concerns

### 5. Type Safety
Both use well-defined interfaces:
- Auth: Minimal interface (3 methods)
- Payments: Comprehensive interface (21 methods)

## Evolution Path

### Adding a New Auth Provider
1. Create `infrastructure/identity/platform/vendors/supabase/client.py`
2. Implement `AuthProviderAdapter` interface
3. Update factory.py
4. Configure in settings.py

### Adding a New Payment Provider
1. Create `infrastructure/payments/providers/paypal.py`
2. Implement `PaymentProviderAdapter` interface
3. Update factory.py
4. Configure in settings.py

**Same process for both!**

## Implementation Checklist

When creating a new abstraction layer, follow this pattern:

- [ ] Create `infrastructure/[domain]/` directory
- [ ] Define abstract adapter class with clear interface
- [ ] Implement at least one provider
- [ ] Create factory function for provider selection
- [ ] Add Django app configuration
- [ ] Document with README and examples
- [ ] Add configuration to settings.py
- [ ] Create comprehensive tests

Both authentication and payment abstractions followed this checklist exactly.

## Key Differences

While the pattern is the same, there are some differences based on domain requirements:

| Aspect | Authentication | Payments |
|--------|---------------|----------|
| **Complexity** | Simple (3 methods) | Complex (21 methods) |
| **State Management** | Stateless (session tokens) | Stateful (subscriptions, invoices) |
| **Data Model** | Minimal (user info) | Rich (customers, subscriptions, payments) |
| **Webhooks** | Not typically used | Essential for status updates |
| **Multi-tenancy** | App-based (app_name param) | Single provider per instance |

## Conclusion

The payment abstraction layer successfully mirrors the authentication abstraction pattern, demonstrating that this architectural approach can be applied consistently across different domains.

**Benefits Realized:**
- ✅ Consistent architecture across infrastructure layers
- ✅ Easy to understand for developers familiar with auth pattern
- ✅ Provider independence for both auth and payments
- ✅ Extensible design for future providers
- ✅ Same testing approaches
- ✅ Clear documentation pattern

This pattern can be extended to other domains like:
- Email providers (SendGrid, Mailgun, SES)
- SMS providers (Twilio, Vonage)
- Storage providers (S3, GCS, Azure)
- Analytics providers (Mixpanel, Amplitude)
