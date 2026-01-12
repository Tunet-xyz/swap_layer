# Infrastructure Abstractions Overview

This document provides a comprehensive overview of all infrastructure abstractions in SwapLayer, explaining the consistent architectural pattern and how to use them effectively.

## Table of Contents

1. [Overview](#overview)
2. [Architectural Pattern](#architectural-pattern)
3. [All Abstractions](#all-abstractions)
4. [Comparison Matrix](#comparison-matrix)
5. [Benefits](#benefits)
6. [Usage Patterns](#usage-patterns)
7. [Testing Strategy](#testing-strategy)
8. [Best Practices](#best-practices)
9. [Adding New Abstractions](#adding-new-abstractions)

## Overview

SwapLayer uses a **Provider Adapter Pattern** for all infrastructure concerns. This architectural approach allows the application to switch between different third-party service providers without changing business logic code.

### What is a Provider Abstraction?

A provider abstraction is a wrapper layer that:
- Defines a consistent interface for a service category (e.g., email, payments, storage)
- Implements provider-specific logic in separate adapter classes
- Uses a factory function to instantiate the configured provider
- Allows switching providers via configuration (no code changes)

### Why Use Abstractions?

**Before Abstraction:**
```python
# Direct Stripe usage - tightly coupled
import stripe
customer = stripe.Customer.create(email='user@example.com')
subscription = stripe.Subscription.create(customer=customer.id, items=[...])
```

**After Abstraction:**
```python
# Provider-agnostic - loosely coupled
from swap_layer.payments.factory import get_payment_provider
provider = get_payment_provider()
customer = provider.create_customer(email='user@example.com')
subscription = provider.create_subscription(customer_id=customer['id'], price_id='...')
```

**Benefits:**
- Switch from Stripe to PayPal by changing one config setting
- Mock easily in tests
- Compare providers without rewriting code
- Future-proof against provider changes

## Architectural Pattern

All abstractions follow this consistent structure:

```
src/swap_layer/{service}/
├── __init__.py              # Package initialization
├── apps.py                  # Django app configuration
├── adapter.py               # Abstract base class (ABC)
├── factory.py               # Provider factory function
├── README.md                # Documentation
└── providers/
    ├── __init__.py
    ├── provider1.py         # Full implementation
    ├── provider2.py         # Full implementation
    └── provider3.py         # Stub for future implementation
```

### Key Components

#### 1. Abstract Base Class (adapter.py)

Defines the interface that all providers must implement:

```python
from abc import ABC, abstractmethod

class ServiceProviderAdapter(ABC):
    @abstractmethod
    def operation(self, params):
        """Perform an operation."""
        pass
```

#### 2. Provider Implementations (providers/)

Concrete implementations for specific providers:

```python
class StripePaymentProvider(PaymentProviderAdapter):
    def __init__(self):
        self.client = stripe  # Initialize provider SDK
    
    def create_customer(self, email, name=None):
        # Stripe-specific implementation
        customer = stripe.Customer.create(email=email, name=name)
        # Normalize response
        return {'id': customer.id, 'email': customer.email, ...}
```

#### 3. Factory Function (factory.py)

Selects and instantiates the configured provider:

```python
def get_payment_provider():
    provider = settings.PAYMENT_PROVIDER  # 'stripe', 'paypal', etc.
    if provider == 'stripe':
        return StripePaymentProvider()
    elif provider == 'paypal':
        return PayPalPaymentProvider()
    # ...
```

#### 4. Configuration (settings.py)

Provider selection and credentials:

```python
# Provider Selection
PAYMENT_PROVIDER = 'stripe'

# Provider Credentials
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
```

## All Abstractions

### 1. Authentication (`infrastructure/identity/platform/`)

**Purpose:** User authentication and authorization

**Providers:**
- WorkOS (SSO, Directory Sync)
- Auth0 (Social login, MFA)

**Key Operations:**
- `get_authorization_url()` - Generate OAuth URL
- `exchange_code_for_user()` - Exchange code for user data
- `get_logout_url()` - Generate logout URL

**Use Cases:** Single sign-on, social login, enterprise authentication

### 2. Identity Verification (`infrastructure/identity/verification/`)

**Purpose:** User identity verification and KYC (Know Your Customer)

**Providers:**
- Stripe Identity (full implementation)
- Onfido (future)

**Key Operations:**
- `create_verification_session()` - Create verification session
- `get_verification_session()` - Retrieve session details
- `cancel_verification_session()` - Cancel session
- `redact_verification_session()` - Remove PII data
- `get_verification_report()` - Get verification report
- `get_verification_insights()` - Get session insights
- `handle_webhook()` - Process webhooks

**Use Cases:** Identity verification, age verification, document verification, compliance

### 3. Payments (`infrastructure/payments/`)

**Purpose:** Payment processing and subscription management

**Providers:**
- Stripe (full implementation)
- PayPal, Square (future)

**Key Operations:** 21 methods including:
- Customer management
- Subscription lifecycle
- Payment methods
- One-time payments
- Checkout sessions
- Invoices
- Webhooks

**Use Cases:** SaaS billing, subscriptions, one-time purchases

### 4. Email (`infrastructure/email/`)

**Purpose:** Transactional and marketing email delivery

**Providers:**
- SMTP (built-in)
- SendGrid (full implementation)
- Mailgun, AWS SES (stubs)

**Key Operations:**
- `send_email()` - Send individual emails
- `send_template_email()` - Template-based emails
- `send_bulk_email()` - Bulk sending with personalization
- `verify_email()` - Email validation
- `get_send_statistics()` - Delivery metrics
- Suppression list management
- Webhook validation

**Use Cases:** Welcome emails, password resets, notifications, newsletters

### 5. Storage (`infrastructure/storage/`)

**Purpose:** File storage and retrieval

**Providers:**
- Local filesystem (full implementation)
- AWS S3 (stub)
- Azure Blob Storage (stub)

**Key Operations:**
- File upload/download/delete
- File metadata and listing
- URL generation (signed URLs)
- Presigned upload URLs
- Copy/move operations
- Bulk operations

**Use Cases:** User uploads, images, documents, backups

### 6. SMS (`infrastructure/sms/`)

**Purpose:** Text message delivery

**Providers:**
- Twilio (full implementation)
- AWS SNS (stub)

**Key Operations:**
- `send_sms()` - Send messages
- `send_bulk_sms()` - Bulk sending
- `get_message_status()` - Delivery status
- `validate_phone_number()` - Validation
- `get_account_balance()` - Check credits
- `list_messages()` - Message history
- Opt-in/opt-out management

**Use Cases:** 2FA, notifications, verification codes, alerts

## Comparison Matrix

| Abstraction | Location | Methods | Providers | Config Key | Full Impl |
|-------------|----------|---------|-----------|------------|-----------|
| **Authentication** | `infrastructure/identity/platform/` | 3 | Auth0, WorkOS | `IDENTITY_PROVIDER` | 2 |
| **Identity Verification** | `infrastructure/identity/verification/` | 8 | Stripe Identity | `IDENTITY_VERIFICATION_PROVIDER` | 1 |
| **Payments** | `infrastructure/payments/` | 21 | Stripe + stubs | `PAYMENT_PROVIDER` | 1 |
| **Email** | `infrastructure/email/` | 8 | SMTP, SendGrid + stubs | `EMAIL_PROVIDER` | 2 |
| **Storage** | `infrastructure/storage/` | 12 | Local + stubs | `STORAGE_PROVIDER` | 1 |
| **SMS** | `infrastructure/sms/` | 8 | Twilio + stub | `SMS_PROVIDER` | 1 |

### Provider Implementation Status

✅ **Fully Implemented** - Production-ready  
🚧 **Stub** - Interface defined, needs implementation  
❌ **Not Started** - Future consideration

| Provider | Status | Abstraction |
|----------|--------|-------------|
| WorkOS | ✅ | Authentication |
| Auth0 | ✅ | Authentication |
| Stripe Identity | ✅ | Identity Verification |
| Onfido | 🚧 | Identity Verification |
| Stripe | ✅ | Payments |
| PayPal | 🚧 | Payments |
| SMTP | ✅ | Email |
| SendGrid | ✅ | Email |
| Mailgun | 🚧 | Email |
| AWS SES | 🚧 | Email |
| Local Filesystem | ✅ | Storage |
| AWS S3 | 🚧 | Storage |
| Azure Blob | 🚧 | Storage |
| Twilio | ✅ | SMS |
| AWS SNS | 🚧 | SMS |

## Benefits

### 1. Provider Independence

Switch providers by changing one configuration setting:

```python
# Before: Using Stripe
PAYMENT_PROVIDER = 'stripe'

# After: Switching to PayPal (once implemented)
PAYMENT_PROVIDER = 'paypal'
```

No code changes required in your application!

### 2. Easy Testing

Mock the abstraction layer instead of the provider SDK:

```python
from unittest.mock import Mock

mock_provider = Mock(spec=PaymentProviderAdapter)
mock_provider.create_customer.return_value = {'id': 'cus_test'}

with patch('infrastructure.payments.factory.get_payment_provider', return_value=mock_provider):
    # Run tests
    pass
```

### 3. Consistent Interface

Same API across all providers:

```python
# Works with any email provider
provider = get_email_provider()
provider.send_email(
    to=['user@example.com'],
    subject='Welcome!',
    html_body='<h1>Hello!</h1>'
)
```

### 4. Cost Optimization

Compare providers and switch to the most cost-effective option without code changes.

### 5. Risk Mitigation

Avoid vendor lock-in. If a provider has issues or increases prices dramatically, switching is easy.

### 6. Multi-Provider Support

Use different providers for different purposes:

```python
# Use SendGrid for marketing emails
if email_type == 'marketing':
    settings.EMAIL_PROVIDER = 'sendgrid'
else:
    settings.EMAIL_PROVIDER = 'ses'  # AWS SES for transactional
```

### 7. Gradual Migration

Migrate from one provider to another gradually without breaking production.

## Usage Patterns

### Pattern 1: Direct Usage

```python
from infrastructure.payments.factory import get_payment_provider

def create_subscription(user, plan):
    provider = get_payment_provider()
    
    # Create customer
    customer = provider.create_customer(
        email=user.email,
        name=user.get_full_name()
    )
    
    # Create subscription
    subscription = provider.create_subscription(
        customer_id=customer['id'],
        price_id=plan.stripe_price_id
    )
    
    return subscription
```

### Pattern 2: Service Layer

```python
# services/payment_service.py
class PaymentService:
    def __init__(self):
        self.provider = get_payment_provider()
    
    def subscribe_user(self, user, plan):
        customer = self.provider.create_customer(...)
        subscription = self.provider.create_subscription(...)
        # Save to database
        return subscription
```

### Pattern 3: Dependency Injection

```python
class SubscriptionManager:
    def __init__(self, payment_provider=None):
        self.provider = payment_provider or get_payment_provider()
    
    def create(self, user, plan):
        # Use self.provider
        pass

# In tests
manager = SubscriptionManager(payment_provider=mock_provider)
```

## Testing Strategy

### Unit Tests

Mock the abstraction layer:

```python
from unittest.mock import Mock, patch
from infrastructure.payments.adapter import PaymentProviderAdapter

def test_create_subscription():
    mock_provider = Mock(spec=PaymentProviderAdapter)
    mock_provider.create_customer.return_value = {'id': 'cus_123'}
    mock_provider.create_subscription.return_value = {'id': 'sub_123'}
    
    with patch('infrastructure.payments.factory.get_payment_provider', return_value=mock_provider):
        result = create_subscription(user, plan)
        assert result['id'] == 'sub_123'
        mock_provider.create_customer.assert_called_once()
```

### Integration Tests

Test with actual providers (use test mode/sandbox):

```python
def test_stripe_integration():
    # Set to test mode
    settings.STRIPE_SECRET_KEY = 'sk_test_...'
    
    provider = get_payment_provider()
    customer = provider.create_customer(email='test@example.com')
    
    assert 'id' in customer
    assert customer['email'] == 'test@example.com'
```

### Provider Tests

Test provider implementations directly:

```python
def test_stripe_provider():
    provider = StripePaymentProvider()
    customer = provider.create_customer(email='test@example.com')
    assert customer['id'].startswith('cus_')
```

## Best Practices

### 1. Configuration

Store all credentials in environment variables:

```python
# settings.py
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
```

Never commit credentials to version control.

### 2. Error Handling

Always wrap provider calls in try-except:

```python
from infrastructure.payments.adapter import PaymentProviderAdapter
from infrastructure.payments.factory import get_payment_provider

try:
    provider = get_payment_provider()
    result = provider.create_customer(email=user.email)
except PaymentError as e:
    logger.error(f"Payment error: {e}")
    # Handle gracefully
```

### 3. Logging

Log all provider interactions:

```python
import logging

logger = logging.getLogger(__name__)

provider = get_payment_provider()
logger.info(f"Creating customer for {user.email}")
customer = provider.create_customer(email=user.email)
logger.info(f"Customer created: {customer['id']}")
```

### 4. Idempotency

Use idempotency keys for operations that shouldn't be duplicated:

```python
provider.create_payment_intent(
    amount=1000,
    metadata={'idempotency_key': f'order_{order.id}'}
)
```

### 5. Async Operations

Use background tasks for non-critical operations:

### 6. Monitoring

Monitor provider health and costs:

```python
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Check SMS balance
        sms = get_sms_provider()
        balance = sms.get_account_balance()
        if balance['balance'] < 100:
            send_alert('Low SMS balance!')
```

## Adding New Abstractions

To add a new abstraction (e.g., Search):

### 1. Create Directory Structure

```
infrastructure/search/
├── __init__.py
├── apps.py
├── adapter.py
├── factory.py
├── README.md
└── providers/
    ├── __init__.py
    ├── elasticsearch.py
    └── algolia.py
```

### 2. Define Abstract Base Class

```python
# adapter.py
from abc import ABC, abstractmethod

class SearchProviderAdapter(ABC):
    @abstractmethod
    def index_document(self, index, document_id, document):
        pass
    
    @abstractmethod
    def search(self, index, query):
        pass
    
    # ... more methods
```

### 3. Implement Providers

```python
# providers/elasticsearch.py
class ElasticsearchSearchProvider(SearchProviderAdapter):
    def __init__(self):
        from elasticsearch import Elasticsearch
        self.client = Elasticsearch(...)
    
    def index_document(self, index, document_id, document):
        return self.client.index(index=index, id=document_id, body=document)
    
    # ... implement other methods
```

### 4. Create Factory

```python
# factory.py
def get_search_provider():
    provider = settings.SEARCH_PROVIDER
    if provider == 'elasticsearch':
        return ElasticsearchSearchProvider()
    # ...
```

### 5. Configure

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'infrastructure.search',
]

SEARCH_PROVIDER = 'elasticsearch'
ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
```

### 6. Document

Create a comprehensive README.md following the same pattern as other abstractions.

## Migration Guide

### From Direct Provider Usage to Abstraction

**Before:**
```python
import stripe
customer = stripe.Customer.create(email='user@example.com')
```

**After:**
```python
from infrastructure.payments.factory import get_payment_provider
provider = get_payment_provider()
customer = provider.create_customer(email='user@example.com')
```

**Steps:**
1. Replace direct SDK imports with factory imports
2. Replace provider-specific calls with abstraction methods
3. Update tests to mock the abstraction layer
4. Update configuration with provider selection

## Conclusion

The infrastructure abstractions in SwapLayer provide a consistent, maintainable approach to integrating third-party services. By following the Provider Adapter Pattern, we gain:

- **Flexibility** - Switch providers easily
- **Testability** - Mock cleanly in tests
- **Consistency** - Same pattern everywhere
- **Maintainability** - Changes are isolated
- **Cost Optimization** - Compare and switch providers
- **Risk Mitigation** - Avoid vendor lock-in

All new infrastructure integrations should follow this pattern for maximum benefit and consistency.

## Further Reading

- [Authentication Abstraction](identity-platform.md)
- [Identity Verification Abstraction](identity-verification.md)
- [Payment Abstraction](billing.md)
- [Email Abstraction](email.md)
- [Storage Abstraction](storage.md)
- [SMS Abstraction](sms.md)

---

**Built with ❤️ by SwapLayer**
