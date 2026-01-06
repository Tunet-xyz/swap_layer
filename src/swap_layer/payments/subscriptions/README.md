# Subscription Management Subdomain

This subdomain handles all subscription-related operations in the payment system.

## Purpose

The Subscription subdomain provides a unified interface for managing recurring subscriptions across different payment processors (Stripe, PayPal, Square, etc.).

## Operations

### Subscription Lifecycle

- **create_subscription**: Create a new subscription for a customer
- **get_subscription**: Retrieve subscription details
- **update_subscription**: Update subscription (e.g., change plan)
- **cancel_subscription**: Cancel a subscription
- **list_subscriptions**: List subscriptions for a customer

## Usage Example

```python
from swap_layer.payments.factory import get_payment_provider

provider = get_payment_provider()

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

## Normalized Data Format

### Subscription Response
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

### Status Values
- `active`: Subscription is active
- `past_due`: Payment failed, but subscription is still active
- `canceled`: Subscription has been canceled
- `incomplete`: Initial payment has not been received
- `trialing`: Subscription is in trial period

## Error Handling

All methods may raise:
- `PaymentValidationError`: If input data is invalid
- `PaymentConnectionError`: If provider is unreachable
- `ResourceNotFoundError`: If subscription or customer is not found
- `PaymentError`: For other payment-related errors

## Related Subdomains

- **Customers**: Manage customer information
- **Payment Intents**: Process one-time payments
- **Products**: Manage subscription pricing and plans
