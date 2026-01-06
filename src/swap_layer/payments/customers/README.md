# Customer Management Subdomain

This subdomain handles all customer-related operations in the payment system.

## Purpose

The Customer subdomain provides a unified interface for managing payment provider customers across different payment processors (Stripe, PayPal, Square, etc.).

## Operations

### Customer Management

- **create_customer**: Create a new customer in the payment provider
- **get_customer**: Retrieve customer details
- **update_customer**: Update customer information
- **delete_customer**: Delete a customer from the provider

## Usage Example

```python
from swap_layer.payments.factory import get_payment_provider

provider = get_payment_provider()

# Create a customer
customer = provider.create_customer(
    email='user@example.com',
    name='John Doe',
    metadata={'user_id': '123'}
)

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

## Normalized Data Format

### Customer Response
```python
{
    'id': 'cus_123',
    'email': 'user@example.com',
    'name': 'John Doe',
    'created': 1234567890,
    'metadata': {'user_id': '123'}
}
```

## Error Handling

All methods may raise:
- `PaymentValidationError`: If input data is invalid
- `PaymentConnectionError`: If provider is unreachable
- `ResourceNotFoundError`: If customer is not found
- `PaymentError`: For other payment-related errors

## Related Subdomains

- **Subscriptions**: Manage customer subscriptions
- **Payment Intents**: Process customer payments
- **Products**: View products available to customers
