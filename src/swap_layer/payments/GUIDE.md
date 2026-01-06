# Payments Module - Quick Start Guide

This guide shows you how to migrate from direct payment provider usage to the SwapLayer payments abstraction.

## Why Use the Abstraction?

**Before** (Direct Stripe usage - vendor lock-in):
```python
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
customer = stripe.Customer.create(email='user@example.com')
subscription = stripe.Subscription.create(customer=customer.id, items=[...])
```

**After** (Provider-agnostic - swap anytime):
```python
from swap_layer.payments.factory import get_payment_provider
payments = get_payment_provider()
customer = payments.create_customer(email='user@example.com')
subscription = payments.create_subscription(customer_id=customer['id'], price_id='...')
```

✅ Change provider by changing ONE setting  
✅ Test with mocks instead of real API calls  
✅ No vendor lock-in

---

---

## Quick Migration Examples

### 1. Customer Operations

**Before:**
```python
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Create customer
customer = stripe.Customer.create(
    email='user@example.com',
    name='John Doe',
    metadata={'user_id': '123'}
)
customer_id = customer.id

# Get customer
customer = stripe.Customer.retrieve('cus_123')

# Update customer
customer = stripe.Customer.modify(
    'cus_123',
    email='newemail@example.com'
)

# Delete customer
stripe.Customer.delete('cus_123')
```

#### After: Payment Abstraction
```python
from swap_layer.payments.factory import get_payment_provider

provider = get_payment_provider()

# Create customer
customer = provider.create_customer(
    email='user@example.com',
    name='John Doe',
    metadata={'user_id': '123'}
)
customer_id = customer['id']

# Get customer
customer = provider.get_customer('cus_123')

# Update customer
customer = provider.update_customer(
    customer_id='cus_123',
    email='newemail@example.com'
)

# Delete customer
provider.delete_customer(customer_id='cus_123')
```

### Subscription Operations

#### Before: Direct Stripe
```python
# Create subscription
subscription = stripe.Subscription.create(
    customer='cus_123',
    items=[{'price': 'price_abc'}],
    trial_period_days=14
)

# Get subscription
subscription = stripe.Subscription.retrieve('sub_123')

# Update subscription
subscription = stripe.Subscription.modify(
    'sub_123',
    items=[{
        'id': subscription['items']['data'][0].id,
        'price': 'price_xyz',
    }]
)

# Cancel subscription
subscription = stripe.Subscription.modify(
    'sub_123',
    cancel_at_period_end=True
)
# OR cancel immediately
subscription = stripe.Subscription.delete('sub_123')

# List subscriptions
subscriptions = stripe.Subscription.list(
    customer='cus_123',
    status='active'
)
```

#### After: Payment Abstraction
```python
provider = get_payment_provider()

# Create subscription
subscription = provider.create_subscription(
    customer_id='cus_123',
    price_id='price_abc',
    trial_period_days=14
)

# Get subscription
subscription = provider.get_subscription('sub_123')

# Update subscription
subscription = provider.update_subscription(
    subscription_id='sub_123',
    price_id='price_xyz'
)

# Cancel subscription
subscription = provider.cancel_subscription(
    subscription_id='sub_123',
    at_period_end=True
)
# OR cancel immediately
subscription = provider.cancel_subscription(
    subscription_id='sub_123',
    at_period_end=False
)

# List subscriptions
subscriptions = provider.list_subscriptions(
    customer_id='cus_123',
    status='active'
)
```

### Payment Methods

#### Before: Direct Stripe
```python
# Attach payment method
payment_method = stripe.PaymentMethod.attach(
    'pm_123',
    customer='cus_123'
)

# List payment methods
payment_methods = stripe.PaymentMethod.list(
    customer='cus_123',
    type='card'
)

# Set default payment method
customer = stripe.Customer.modify(
    'cus_123',
    invoice_settings={'default_payment_method': 'pm_123'}
)

# Detach payment method
payment_method = stripe.PaymentMethod.detach('pm_123')
```

#### After: Payment Abstraction
```python
provider = get_payment_provider()

# Attach payment method
payment_method = provider.attach_payment_method(
    customer_id='cus_123',
    payment_method_id='pm_123'
)

# List payment methods
payment_methods = provider.list_payment_methods(
    customer_id='cus_123',
    method_type='card'
)

# Set default payment method
customer = provider.set_default_payment_method(
    customer_id='cus_123',
    payment_method_id='pm_123'
)

# Detach payment method
payment_method = provider.detach_payment_method('pm_123')
```

### Payment Intents (One-time Payments)

#### Before: Direct Stripe
```python
from decimal import Decimal

# Create payment intent
payment_intent = stripe.PaymentIntent.create(
    amount=500,  # £5.00 in pence
    currency='gbp',
    customer='cus_123',
    metadata={'order_id': 'ord_123'}
)
client_secret = payment_intent.client_secret

# Confirm payment intent
payment_intent = stripe.PaymentIntent.confirm(
    payment_intent.id,
    payment_method='pm_123'
)

# Get payment intent
payment_intent = stripe.PaymentIntent.retrieve('pi_123')
```

#### After: Payment Abstraction
```python
from decimal import Decimal

provider = get_payment_provider()

# Create payment intent
payment_intent = provider.create_payment_intent(
    amount=Decimal('500'),  # £5.00 in pence
    currency='gbp',
    customer_id='cus_123',
    metadata={'order_id': 'ord_123'}
)
client_secret = payment_intent['client_secret']

# Confirm payment intent
payment_intent = provider.confirm_payment_intent(
    payment_intent_id=payment_intent['id'],
    payment_method_id='pm_123'
)

# Get payment intent
payment_intent = provider.get_payment_intent('pi_123')
```

### Checkout Sessions

#### Before: Direct Stripe
```python
# Create checkout session
session = stripe.checkout.Session.create(
    customer='cus_123',
    line_items=[{'price': 'price_abc', 'quantity': 1}],
    mode='subscription',
    success_url='https://example.com/success',
    cancel_url='https://example.com/cancel'
)
checkout_url = session.url

# Get checkout session
session = stripe.checkout.Session.retrieve('cs_123')
```

#### After: Payment Abstraction
```python
provider = get_payment_provider()

# Create checkout session
session = provider.create_checkout_session(
    customer_id='cus_123',
    price_id='price_abc',
    success_url='https://example.com/success',
    cancel_url='https://example.com/cancel',
    mode='subscription'
)
checkout_url = session['url']

# Get checkout session
session = provider.get_checkout_session('cs_123')
```

### Webhooks

#### Before: Direct Stripe
```python
import stripe

def webhook_view(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)
    
    # Handle event
    if event['type'] == 'customer.subscription.created':
        subscription = event['data']['object']
        # Process subscription
    
    return HttpResponse(status=200)
```

#### After: Payment Abstraction
```python
from swap_layer.payments.factory import get_payment_provider

def webhook_view(request):
    provider = get_payment_provider()
    
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    
    try:
        event = provider.verify_webhook_signature(
            payload=payload,
            signature=sig_header,
            webhook_secret=webhook_secret
        )
    except ValueError as e:
        return HttpResponse(status=400)
    
    # Handle event (normalized format)
    if event['type'] == 'customer.subscription.created':
        subscription = event['data']
        # Process subscription
    
    return HttpResponse(status=200)
```

## Using the Subscription Service (Recommended)

Instead of using the low-level payment provider directly, use the subscription service for automatic database syncing:

### Before: Manual Stripe + Database Management
```python
import stripe
from myapp.models import UserSubscription

def create_subscription_view(request):
    # Create in Stripe
    customer = stripe.Customer.create(email=request.user.email)
    subscription = stripe.Subscription.create(
        customer=customer.id,
        items=[{'price': 'price_abc'}]
    )
    
    # Save to database manually
    UserSubscription.objects.create(
        user=request.user,
        stripe_customer_id=customer.id,
        stripe_subscription_id=subscription.id,
        status=subscription.status,
        current_period_end=subscription.current_period_end
    )
```

### After: Subscription Service (Automatic Sync)
```python
from services.subscriptions.operations.core import SubscriptionOperations
from services.subscriptions.schemas import SubscriptionCreate

def create_subscription_view(request):
    ops = SubscriptionOperations()
    
    # Get or create customer (automatic)
    customer = ops.get_or_create_customer(request.user)
    
    # Create subscription (automatic provider + DB)
    subscription_data = SubscriptionCreate(
        price_id='price_abc',
        trial_period_days=14
    )
    subscription = ops.create_subscription(customer, subscription_data)
    
    # subscription is a Django model with all data synced
```

## Migration Steps

### 1. Update Imports
Replace all `import stripe` with:
```python
from swap_layer.payments.factory import get_payment_provider
```

### 2. Replace Direct Stripe Calls
Use the quick reference above to convert each Stripe call to the abstraction layer.

### 3. Handle Data Normalization
The abstraction returns dictionaries instead of Stripe objects:

**Before:**
```python
customer = stripe.Customer.retrieve('cus_123')
print(customer.email)  # Attribute access
print(customer['email'])  # Also works
```

**After:**
```python
provider = get_payment_provider()
customer = provider.get_customer('cus_123')
print(customer['email'])  # Dictionary access only
```

### 4. Update Error Handling
Provider-specific errors are normalized:

**Before:**
```python
try:
    customer = stripe.Customer.create(email='invalid')
except stripe.error.InvalidRequestError as e:
    handle_error(e)
```

**After:**
```python
try:
    provider = get_payment_provider()
    customer = provider.create_customer(email='invalid')
except ValueError as e:
    handle_error(e)
```

### 5. Update Tests
Replace Stripe mocking with provider mocking:

**Before:**
```python
@patch('stripe.Customer.create')
def test_create_customer(mock_create):
    mock_create.return_value = Mock(id='cus_123')
    # test code
```

**After:**
```python
from swap_layer.payments.adapter import PaymentProviderAdapter

@patch('swap_layer.payments.factory.get_payment_provider')
def test_create_customer(mock_get_provider):
    mock_provider = Mock(spec=PaymentProviderAdapter)
    mock_provider.create_customer.return_value = {'id': 'cus_123'}
    mock_get_provider.return_value = mock_provider
    # test code
```

### 6. Optional: Migrate to Subscription Service
For comprehensive subscription management, migrate to the subscription service:

```python
# Old way: Manual Stripe + separate DB models
stripe_customer = stripe.Customer.create(...)
MyCustomer.objects.create(stripe_id=stripe_customer.id, ...)

# New way: Automatic sync via subscription service
from services.subscriptions.operations.core import SubscriptionOperations
ops = SubscriptionOperations()
customer = ops.get_or_create_customer(user)
```

## Configuration Changes

No configuration changes needed! The abstraction uses existing Stripe settings:

```python
# settings.py - These stay the same
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

# Add this (optional, defaults to 'stripe')
PAYMENT_PROVIDER = 'stripe'
```

## Testing Your Migration

1. **Run existing tests** - They should still pass with minimal changes
2. **Test in development** - Use Stripe test mode
3. **Verify webhooks** - Test webhook handling with Stripe CLI
4. **Check error handling** - Ensure errors are caught properly
5. **Validate data** - Confirm normalized data contains expected fields

## Rollback Plan

If you need to rollback:

1. The abstraction doesn't modify your database schema
2. Your Stripe data is unchanged
3. Simply revert code changes to use `stripe` directly again

## Benefits After Migration

✅ **Provider Independence**: Switch to PayPal by changing one setting  
✅ **Consistent Interface**: Same code for all providers  
✅ **Better Testing**: Mock the adapter interface  
✅ **Type Safety**: Pydantic schemas validate data  
✅ **Database Integration**: Automatic sync via subscription service  
✅ **Future-Proof**: Easy to add new providers

## Common Pitfalls

### 1. Accessing Stripe Objects Directly
**Wrong:**
```python
customer = provider.get_customer('cus_123')
print(customer.email)  # AttributeError!
```

**Right:**
```python
customer = provider.get_customer('cus_123')
print(customer['email'])  # Dictionary access
```

### 2. Not Handling Normalized Data
The abstraction returns standardized dictionaries. Update code that expects Stripe objects.

### 3. Forgetting to Initialize Provider
**Wrong:**
```python
customer = get_payment_provider.create_customer(...)  # Missing ()
```

**Right:**
```python
provider = get_payment_provider()
customer = provider.create_customer(...)
```

## Need Help?

- Check `swap_layer/payments/README.md` for complete API reference
- See `services/subscriptions/USAGE_EXAMPLE.md` for service layer examples
- Review `ARCHITECTURE_COMPARISON.md` for design patterns

## Example: Complete View Migration

### Before
```python
import stripe
from django.shortcuts import render, redirect

def subscribe_view(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    
    if request.method == 'POST':
        customer = stripe.Customer.create(
            email=request.user.email,
            name=request.user.get_full_name()
        )
        
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{'price': request.POST['price_id']}]
        )
        
        # Save to DB manually
        request.user.profile.stripe_customer_id = customer.id
        request.user.profile.stripe_subscription_id = subscription.id
        request.user.profile.save()
        
        return redirect('dashboard')
    
    return render(request, 'subscribe.html')
```

### After (Using Subscription Service)
```python
from services.subscriptions.operations.core import SubscriptionOperations
from services.subscriptions.schemas import SubscriptionCreate

def subscribe_view(request):
    ops = SubscriptionOperations()
    
    if request.method == 'POST':
        # Automatic customer creation + DB sync
        customer = ops.get_or_create_customer(request.user)
        
        # Automatic subscription creation + DB sync
        subscription_data = SubscriptionCreate(
            price_id=request.POST['price_id']
        )
        subscription = ops.create_subscription(customer, subscription_data)
        
        # Done! Everything synced to DB automatically
        return redirect('dashboard')
    
    return render(request, 'subscribe.html')
```

Much cleaner and more maintainable! 🎉
