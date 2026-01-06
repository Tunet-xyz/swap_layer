# SwapLayer Error System - Developer Guide

**World-class error messages that guide you to solutions, not frustration.**

## 🎯 Philosophy

SwapLayer's error system is designed with one goal: **earn your trust by making errors helpful, not cryptic.**

Every error message includes:
- ✅ **Clear description** of what went wrong
- 💡 **Actionable hints** on how to fix it
- 📋 **Valid examples** showing correct values
- 🔍 **Related settings** to check
- 📚 **Documentation links** for more details

## 🚀 Quick Examples

### Before: Generic Error
```python
# Old way - cryptic error
ValueError: Stripe secret key must start with 'sk_'
# Where? What did I provide? What's the correct format?
```

### After: Rich Error
```python
# New way - actionable error
❌ Invalid Stripe secret key

💡 Hint: Stripe secret keys have a specific format. You provided: 'pk_test_51A...'

✅ Valid examples:
   sk_test_51A... (test mode secret key)
   sk_live_51A... (live mode secret key)

🔍 Check these settings:
   - SWAPLAYER.payments.stripe.secret_key
   - SWAPLAYER.payments.stripe.publishable_key

📚 Documentation: https://stripe.com/docs/keys
```

**Result:** You know exactly what's wrong and how to fix it in seconds!

---

## 📚 Error Types

### 1. Configuration Errors

Raised when settings are missing or invalid.

#### StripeKeyError

**Trigger:** Invalid Stripe API key format

```python
# ❌ This will fail
SWAPLAYER = SwapLayerSettings(
    payments={
        'provider': 'stripe',
        'stripe': {'secret_key': 'pk_test_123'}  # Wrong! Used publishable key
    }
)
```

**Error Message:**
```
❌ Invalid Stripe secret key

💡 Hint: Stripe secret keys have a specific format. You provided: 'pk_test_123...'

✅ Valid examples:
   sk_test_51A... (test mode secret key)
   sk_live_51A... (live mode secret key)

🔍 Check these settings:
   - SWAPLAYER.payments.stripe.secret_key
   - SWAPLAYER.payments.stripe.publishable_key

📚 Documentation: https://stripe.com/docs/keys
```

**Fix:**
```python
# ✅ Correct
SWAPLAYER = SwapLayerSettings(
    payments={
        'provider': 'stripe',
        'stripe': {'secret_key': 'sk_test_51A...'}  # Starts with 'sk_'
    }
)
```

---

#### TwilioConfigError

**Trigger:** Invalid Twilio configuration

##### Invalid Account SID

```python
# ❌ This will fail
SWAPLAYER = SwapLayerSettings(
    sms={
        'provider': 'twilio',
        'twilio': {
            'account_sid': 'SK1234567890',  # Wrong! This is a SID, not Account SID
            'auth_token': '...',
            'from_number': '+15555551234'
        }
    }
)
```

**Error Message:**
```
❌ Invalid Twilio Account SID

💡 Hint: Twilio Account SIDs always start with 'AC'. You provided: 'SK12345678...'

✅ Valid examples:
   AC1234567890abcdef1234567890abcd (34 characters)

🔍 Check these settings:
   - SWAPLAYER.sms.twilio.account_sid

📚 Documentation: https://www.twilio.com/docs/iam/keys/api-key
```

##### Invalid Phone Number

```python
# ❌ This will fail
SWAPLAYER = SwapLayerSettings(
    sms={
        'provider': 'twilio',
        'twilio': {
            'account_sid': 'AC...',
            'auth_token': '...',
            'from_number': '555-123-4567'  # Wrong! Not E.164 format
        }
    }
)
```

**Error Message:**
```
❌ Invalid phone number format

💡 Hint: Phone numbers must be in E.164 format (starts with '+' and country code). 
         You provided: '555-123-4567'

✅ Valid examples:
   +15555551234 (US number)
   +442071838750 (UK number)
   +61212345678 (AU number)

🔍 Check these settings:
   - SWAPLAYER.sms.twilio.from_number

📚 Documentation: https://www.twilio.com/docs/glossary/what-e164
```

**Fix:**
```python
# ✅ Correct
SWAPLAYER = SwapLayerSettings(
    sms={
        'provider': 'twilio',
        'twilio': {
            'account_sid': 'AC1234567890abcdef1234567890abcd',
            'auth_token': 'your_auth_token',
            'from_number': '+15555551234'  # E.164 format
        }
    }
)
```

---

#### WorkOSConfigError

**Trigger:** Invalid WorkOS configuration

```python
# ❌ This will fail
SWAPLAYER = SwapLayerSettings(
    identity={
        'provider': 'workos',
        'workos_apps': {
            'default': {
                'api_key': 'sk_prod_...',
                'client_id': 'client_...',
                'cookie_password': 'short123'  # Wrong! Too short
            }
        }
    }
)
```

**Error Message:**
```
❌ Cookie password too short

💡 Hint: Cookie password must be at least 32 characters for security. 
         You provided 8 characters.

✅ Valid examples:
   Generate secure password: python -c 'import secrets; print(secrets.token_urlsafe(32))'
   Or use: openssl rand -base64 32

🔍 Check these settings:
   - SWAPLAYER.identity.workos_apps.<app_name>.cookie_password

📚 Documentation: https://workos.com/docs/user-management/configuration
```

**Fix:**
```bash
# Generate secure password
python -c 'import secrets; print(secrets.token_urlsafe(32))'
# Output: vJk7m2R3pQ9xL4nH8wY6zT1cF5bN0dS7

# Use in settings:
SWAPLAYER = SwapLayerSettings(
    identity={
        'provider': 'workos',
        'workos_apps': {
            'default': {
                'api_key': 'sk_prod_...',
                'client_id': 'client_...',
                'cookie_password': 'vJk7m2R3pQ9xL4nH8wY6zT1cF5bN0dS7'  # ✅ 32+ chars
            }
        }
    }
)
```

---

#### ProviderConfigMismatchError

**Trigger:** Provider selected but configuration missing

```python
# ❌ This will fail
SWAPLAYER = SwapLayerSettings(
    payments={
        'provider': 'stripe',
        # Missing 'stripe' config!
    }
)
```

**Error Message:**
```
❌ Payments provider 'stripe' selected but stripe not configured

💡 Hint: When you set provider='stripe', you must also provide the stripe configuration.

✅ Valid examples:
   payments={'provider': 'stripe', 'stripe': {'secret_key': 'sk_test_...', 'publishable_key': 'pk_test_...'}}

🔍 Check these settings:
   - SWAPLAYER.payments.provider
   - SWAPLAYER.payments.stripe

📚 Documentation: https://github.com/yourusername/swap_layer/blob/main/src/swap_layer/payments/README.md
```

**Fix:**
```python
# ✅ Correct
SWAPLAYER = SwapLayerSettings(
    payments={
        'provider': 'stripe',
        'stripe': {  # Provide the config!
            'secret_key': 'sk_test_...',
            'publishable_key': 'pk_test_...'
        }
    }
)
```

---

#### ModuleNotConfiguredError

**Trigger:** Attempting to use a module that isn't configured

```python
# settings.py - payments not configured
SWAPLAYER = SwapLayerSettings(
    email={'provider': 'django'}
)

# In your code
from swap_layer import get_provider
payments = get_provider('payments')  # ❌ This will fail
```

**Error Message:**
```
❌ SwapLayer 'payments' module is not configured

💡 Hint: You tried to use the payments module, but it's not configured in your settings. 
         Add it to SWAPLAYER settings.

✅ Valid examples:
   # In settings.py
   SWAPLAYER = SwapLayerSettings(
       payments={'provider': 'stripe', 'stripe': {'secret_key': 'sk_test_...'}}
   )

🔍 Check these settings:
   - SWAPLAYER.payments

📚 Documentation: https://github.com/yourusername/swap_layer/blob/main/SETTINGS_MANAGEMENT.md
```

**Fix:**
```python
# ✅ Correct - configure the module first
SWAPLAYER = SwapLayerSettings(
    email={'provider': 'django'},
    payments={'provider': 'stripe', 'stripe': {'secret_key': 'sk_test_...'}}  # Add this
)
```

---

### 2. Validation Errors at Startup

When you have multiple configuration errors, SwapLayer shows them all at once:

```python
# ❌ Multiple errors
SWAPLAYER = SwapLayerSettings(
    payments={
        'provider': 'stripe',
        'stripe': {'secret_key': 'pk_test_123'}  # Wrong key type
    },
    sms={
        'provider': 'twilio',
        'twilio': {
            'account_sid': 'SK123',  # Wrong prefix
            'auth_token': '...',
            'from_number': '555-1234'  # Not E.164
        }
    }
)
```

**Error Message:**
```
================================================================================
🚨 SWAPLAYER CONFIGURATION VALIDATION FAILED
================================================================================

The following configuration errors were found:

1. ❌ payments → stripe → secret_key
   Error: Stripe secret key must start with 'sk_'
   Type: value_error

2. ❌ sms → twilio → account_sid
   Error: Twilio Account SID must start with 'AC'
   Type: value_error

3. ❌ sms → twilio → from_number
   Error: Phone number must be in E.164 format
   Type: value_error

💡 Tips:
  • Run: python manage.py swaplayer_check --verbose
  • Check: SETTINGS_MANAGEMENT.md for configuration guide
  • See: CONFIGURATION_EXAMPLES.md for examples

================================================================================
```

**Result:** You see ALL errors at once and can fix them together!

---

## 🛠️ Using Errors in Your Code

### Catching Specific Errors

```python
from swap_layer import get_provider, ModuleNotConfiguredError, ConfigurationError

try:
    payments = get_provider('payments')
except ModuleNotConfiguredError as e:
    # Handle module not configured
    print("Payments not configured, skipping payment features")
    print(e)  # Shows helpful error with hints
except ConfigurationError as e:
    # Handle other configuration errors
    print("Configuration error:", e)
```

### Custom Error Handling

```python
from swap_layer.exceptions import SwapLayerError

def process_payment(amount):
    try:
        payments = get_provider('payments')
        result = payments.create_charge(amount)
    except SwapLayerError as e:
        # All SwapLayer errors inherit from SwapLayerError
        # Log the full error with context
        logger.error(f"Payment failed: {e}")
        
        # Show user-friendly message
        if hasattr(e, 'hint'):
            return f"Configuration issue: {e.hint}"
        return "Payment system unavailable"
```

### Health Check Integration

```python
# views.py
from django.http import JsonResponse
from swap_layer import validate_swaplayer_config

def health_check(request):
    result = validate_swaplayer_config()
    
    if not result['valid']:
        return JsonResponse({
            'status': 'error',
            'message': result['error'],
            'details': 'Check SwapLayer configuration'
        }, status=500)
    
    return JsonResponse({
        'status': 'healthy',
        'modules': result['modules']
    })
```

---

## 🎓 Best Practices

### 1. Validate Early

Run configuration validation during startup:

```python
# settings.py (at the end)
from swap_layer import validate_swaplayer_config

# Validate on startup in production
if not DEBUG:
    result = validate_swaplayer_config()
    if not result['valid']:
        raise RuntimeError(f"SwapLayer config invalid: {result['error']}")
```

### 2. Use the Management Command

Check configuration before deployment:

```bash
# Validate configuration
python manage.py swaplayer_check

# Verbose output with full config
python manage.py swaplayer_check --verbose

# Check specific module
python manage.py swaplayer_check --module payments
```

### 3. Handle Errors Gracefully

```python
from swap_layer import get_provider
from swap_layer.exceptions import SwapLayerError

class PaymentService:
    def __init__(self):
        try:
            self.provider = get_provider('payments')
            self.available = True
        except SwapLayerError as e:
            logger.warning(f"Payments unavailable: {e.hint if hasattr(e, 'hint') else str(e)}")
            self.provider = None
            self.available = False
    
    def process_payment(self, amount):
        if not self.available:
            raise ValueError("Payment system not configured")
        return self.provider.create_charge(amount)
```

### 4. Environment-Specific Error Handling

```python
# settings/base.py
SWAPLAYER_RAISE_ON_ERROR = True  # Fail fast by default

# settings/development.py
SWAPLAYER_RAISE_ON_ERROR = False  # More forgiving in dev

# settings/production.py  
SWAPLAYER_RAISE_ON_ERROR = True  # Strict in production
```

---

## 🔥 Common Error Patterns & Solutions

### Pattern 1: "I forgot to configure a module"

**Error:**
```
ModuleNotConfiguredError: SwapLayer 'payments' module is not configured
```

**Solution:**
```python
# Add the module to your settings
SWAPLAYER = SwapLayerSettings(
    payments={'provider': 'stripe', 'stripe': {...}}
)
```

### Pattern 2: "I used the wrong API key"

**Error:**
```
StripeKeyError: Invalid Stripe secret key
Hint: You provided: 'pk_test_...' (this is a publishable key)
```

**Solution:**
```python
# Use the secret key (starts with 'sk_')
'secret_key': 'sk_test_...'  # ✅
'publishable_key': 'pk_test_...'  # ✅ (if needed)
```

### Pattern 3: "Phone number format wrong"

**Error:**
```
TwilioConfigError: Invalid phone number format
Hint: Phone numbers must be in E.164 format
```

**Solution:**
```python
# Convert to E.164 format
'from_number': '+15555551234'  # ✅ +[country code][number]
```

### Pattern 4: "Environment variables not loading"

**Error:**
```
EnvironmentVariableError: Missing environment variable SWAPLAYER_PAYMENTS_STRIPE_SECRET_KEY
```

**Solution:**
```bash
# Set the environment variable
export SWAPLAYER_PAYMENTS_STRIPE_SECRET_KEY=sk_test_...

# Or use .env file
echo "SWAPLAYER_PAYMENTS_STRIPE_SECRET_KEY=sk_test_..." >> .env
```

---

## 💎 Advanced: Custom Error Messages

You can extend the error system for your own validation:

```python
from swap_layer.exceptions import SwapLayerError

class CustomValidationError(SwapLayerError):
    """Custom validation for your app."""
    
    def __init__(self, field_name: str, provided_value: str):
        super().__init__(
            f"❌ Invalid {field_name}",
            hint=f"You provided '{provided_value}', but this doesn't match our requirements",
            examples=[
                "Valid example 1",
                "Valid example 2",
            ],
            docs_url="https://your-docs-url.com",
        )

# Use it:
if not is_valid_custom_field(value):
    raise CustomValidationError('custom_field', value)
```

---

## 📊 Error Message Comparison

| Error Type | Old Way | New Way |
|------------|---------|---------|
| **Missing Config** | `KeyError: 'STRIPE_SECRET_KEY'` | `ModuleNotConfiguredError` with examples & hints |
| **Wrong Format** | `ValueError: must start with 'sk_'` | `StripeKeyError` with what you provided & valid examples |
| **Missing Provider Config** | `ValueError: config required` | `ProviderConfigMismatchError` with complete examples |
| **Startup Validation** | Single error, app stops | All errors listed at once with tips |

---

## 🎉 Summary

SwapLayer's error system:
- ✅ **Never leaves you guessing** - always tells you what's wrong
- ✅ **Shows you how to fix it** - with examples and hints
- ✅ **Points you to docs** - for more context
- ✅ **Lists all errors at once** - fix everything in one go
- ✅ **Masks sensitive data** - keeps secrets safe in logs
- ✅ **Works at all levels** - startup, runtime, and debugging

**Result:** Spend seconds fixing errors, not hours debugging! 🚀

---

## 📚 Related Documentation

- [SETTINGS_MANAGEMENT.md](SETTINGS_MANAGEMENT.md) - Complete settings guide
- [CONFIGURATION_EXAMPLES.md](CONFIGURATION_EXAMPLES.md) - Configuration examples
- [SETTINGS_BENEFITS.md](SETTINGS_BENEFITS.md) - Benefits & comparison
- Module READMEs - Specific module documentation

Need help? File an issue: https://github.com/yourusername/swap_layer/issues
