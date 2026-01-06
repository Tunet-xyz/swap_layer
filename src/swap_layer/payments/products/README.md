# Products Subdomain

This subdomain handles product catalog and pricing management.

## Purpose

The Products subdomain provides a unified interface for managing products and their pricing across different payment processors (Stripe, PayPal, Square, etc.).

**Note**: This is a placeholder subdomain for future implementation. The adapter interface is defined but not yet implemented in the Stripe provider.

## Operations

### Product Management
- **create_product**: Create a new product
- **get_product**: Retrieve product details
- **update_product**: Update product information
- **list_products**: List products in the catalog

### Pricing Management
- **create_price**: Create a price for a product
- **get_price**: Retrieve price details
- **list_prices**: List prices for products

## Planned Usage Example

```python
from swap_layer.payments.factory import get_payment_provider
from decimal import Decimal

provider = get_payment_provider()

# Create a product
product = provider.create_product(
    name='Pro Plan',
    description='Professional subscription plan',
    metadata={'tier': 'pro'}
)

# Get product
product = provider.get_product(product_id='prod_123')

# Update product
updated = provider.update_product(
    product_id='prod_123',
    description='Updated description'
)

# List products
products = provider.list_products(
    limit=10,
    active=True
)

# Create a price
price = provider.create_price(
    product_id='prod_123',
    amount=Decimal('2999'),  # $29.99 in cents
    currency='usd',
    recurring={'interval': 'month', 'interval_count': 1},
    metadata={'display_name': 'Monthly'}
)

# Get price
price = provider.get_price(price_id='price_123')

# List prices for a product
prices = provider.list_prices(
    product_id='prod_123',
    limit=10
)
```

## Normalized Data Format

### Product Response
```python
{
    'id': 'prod_123',
    'name': 'Pro Plan',
    'description': 'Professional subscription plan',
    'active': True,
    'metadata': {'tier': 'pro'}
}
```

### Price Response
```python
{
    'id': 'price_123',
    'product_id': 'prod_123',
    'amount': 2999,
    'currency': 'usd',
    'recurring': {
        'interval': 'month',
        'interval_count': 1
    },
    'metadata': {}
}
```

## Error Handling

All methods may raise:
- `PaymentValidationError`: If input data is invalid
- `PaymentConnectionError`: If provider is unreachable
- `ResourceNotFoundError`: If product or price is not found
- `PaymentError`: For other payment-related errors

## Implementation Status

🚧 **Not Yet Implemented**: The product management interface is defined in the adapter but not yet implemented in the Stripe provider or other providers.

To use product and pricing features with Stripe, you can currently:
1. Use the Stripe API directly via the escape hatch: `provider.get_vendor_client()`
2. Manage products through the Stripe Dashboard
3. Reference existing price IDs in subscription creation

Future versions will include full product management support in the abstraction layer.

## Related Subdomains

- **Customers**: Customers who purchase products
- **Subscriptions**: Subscribe customers to products
- **Payment Intents**: Process one-time product purchases
