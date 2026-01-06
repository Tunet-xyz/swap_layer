# Payment Intents Subdomain

This subdomain handles payment intents, payment methods, checkout sessions, invoices, and webhooks.

## Purpose

The Payment Intents subdomain provides a unified interface for processing one-time payments, managing payment methods, creating hosted checkout sessions, handling invoices, and processing webhooks across different payment processors.

## Operations

### Payment Methods
- **attach_payment_method**: Attach a payment method to a customer
- **detach_payment_method**: Detach a payment method from a customer
- **list_payment_methods**: List payment methods for a customer
- **set_default_payment_method**: Set the default payment method

### One-time Payments
- **create_payment_intent**: Create a payment intent for a one-time payment
- **confirm_payment_intent**: Confirm a payment intent
- **get_payment_intent**: Retrieve payment intent details

### Checkout Sessions
- **create_checkout_session**: Create a hosted checkout page
- **get_checkout_session**: Retrieve checkout session details

### Invoices
- **get_invoice**: Retrieve invoice details
- **list_invoices**: List invoices for a customer

### Webhooks
- **verify_webhook_signature**: Verify and parse webhook payloads

## Usage Examples

### Payment Methods
```python
from swap_layer.payments.factory import get_payment_provider

provider = get_payment_provider()

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

### Invoices
```python
# Get invoice
invoice = provider.get_invoice(invoice_id='in_123')

# List invoices
invoices = provider.list_invoices(
    customer_id='cus_123',
    limit=10
)
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

### Payment Intent Response
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

### Payment Method Response
```python
{
    'id': 'pm_123',
    'customer_id': 'cus_123',
    'type': 'card',
    'card': {
        'brand': 'visa',
        'last4': '4242',
        'exp_month': 12,
        'exp_year': 2025
    }
}
```

### Checkout Session Response
```python
{
    'id': 'cs_123',
    'url': 'https://checkout.stripe.com/...',
    'customer_id': 'cus_123',
    'mode': 'subscription'
}
```

### Invoice Response
```python
{
    'id': 'in_123',
    'customer_id': 'cus_123',
    'amount_due': 1000,
    'amount_paid': 1000,
    'status': 'paid'
}
```

## Error Handling

All methods may raise:
- `PaymentValidationError`: If input data is invalid
- `PaymentDeclinedError`: If payment is declined
- `PaymentConnectionError`: If provider is unreachable
- `ResourceNotFoundError`: If resource is not found
- `PaymentError`: For other payment-related errors

## Related Subdomains

- **Customers**: Manage customer information
- **Subscriptions**: Manage recurring subscriptions
- **Products**: View products and pricing
