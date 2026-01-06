# SwapLayer Settings Management 🎛️

**World-class developer experience for managing SwapLayer configuration.**

## Why This Matters

Before:
```python
# 😫 Scattered configuration, no validation, confusing
PAYMENT_PROVIDER = 'stripe'
STRIPE_SECRET_KEY = 'sk_test_...'
EMAIL_PROVIDER = 'django'
SMS_PROVIDER = 'twilio'
TWILIO_ACCOUNT_SID = 'AC...'
TWILIO_AUTH_TOKEN = '...'
TWILIO_FROM_NUMBER = '+1555...'
# What if I make a typo? What if I forget something?
# How do I know what's configured?
```

After:
```python
# ✨ Structured, validated, discoverable
SWAPLAYER = SwapLayerSettings(
    payments={
        'provider': 'stripe',
        'stripe': {'secret_key': os.environ['STRIPE_SECRET_KEY']}
    },
    email={'provider': 'django'},
    sms={
        'provider': 'twilio',
        'twilio': {
            'account_sid': os.environ['TWILIO_ACCOUNT_SID'],
            'auth_token': os.environ['TWILIO_AUTH_TOKEN'],
            'from_number': os.environ['TWILIO_FROM_NUMBER'],
        }
    }
)

# Check what's configured
python manage.py swaplayer_check
```

## 🚀 Quick Start

### 1. Install (if not already)
```bash
pip install swaplayer[all]
```

### 2. Configure in settings.py

**Option A: Structured Configuration (Recommended)**
```python
# settings.py
import os
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    payments={
        'provider': 'stripe',
        'stripe': {'secret_key': os.environ['STRIPE_SECRET_KEY']}
    },
    email={'provider': 'django'},
)
```

**Option B: Environment Variables**
```python
# settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings.from_env()
```

```bash
# .env or environment
SWAPLAYER_PAYMENTS_PROVIDER=stripe
SWAPLAYER_PAYMENTS_STRIPE_SECRET_KEY=sk_test_...
SWAPLAYER_EMAIL_PROVIDER=django
```

### 3. Verify Configuration
```bash
python manage.py swaplayer_check
```

Output:
```
============================================================
SwapLayer Configuration Check
============================================================

✓ payments        configured (provider: stripe)
✓ email           configured (provider: django)
○ sms             not configured
○ storage         not configured
○ identity        not configured
○ verification    not configured

Configured: 2/6 modules

============================================================
Configuration looks good! 🚀
============================================================
```

## ✨ Key Features

### 1. **Type Safety with Pydantic**

Configuration is validated at startup using Pydantic. Get instant feedback on errors:

```python
SWAPLAYER = SwapLayerSettings(
    payments={
        'provider': 'stripe',
        'stripe': {'secret_key': 'pk_test_123'}  # ❌ Error!
    }
)
# ValidationError: Stripe secret key must start with 'sk_'
```

### 2. **IDE Autocomplete**

Your IDE knows all available options:

```python
SWAPLAYER = SwapLayerSettings(
    payments=  # IDE suggests: PaymentsConfig
        provider=  # IDE suggests: 'stripe'
        stripe=  # IDE suggests: StripeConfig
            secret_key=  # IDE shows: str (required)
            publishable_key=  # IDE shows: Optional[str]
```

### 3. **Helpful Error Messages**

No more cryptic errors:

```python
# Missing required field
SWAPLAYER = SwapLayerSettings(
    sms={'provider': 'twilio'}
)
# ValidationError: Twilio configuration required when provider='twilio'

# Invalid value
SWAPLAYER = SwapLayerSettings(
    sms={
        'provider': 'twilio',
        'twilio': {'from_number': '5551234'}  # ❌ Missing +
    }
)
# ValidationError: Phone number must be in E.164 format (e.g., +15555551234)
```

### 4. **Configuration Validation**

Check if everything is set up correctly:

```python
from swap_layer.settings import validate_swaplayer_config

result = validate_swaplayer_config()
if result['valid']:
    print("Configuration OK!")
    print(result['modules'])
else:
    print(f"Error: {result['error']}")
```

### 5. **Management Command**

```bash
# Check all modules
python manage.py swaplayer_check

# Check specific module
python manage.py swaplayer_check --module payments

# Show detailed config (masks secrets)
python manage.py swaplayer_check --verbose
```

### 6. **Backward Compatible**

Existing configurations still work! SwapLayer automatically detects legacy settings:

```python
# Old way - still works!
PAYMENT_PROVIDER = 'stripe'
STRIPE_SECRET_KEY = 'sk_test_...'

# SwapLayer converts this to the new format automatically
```

### 7. **Environment Variable Support**

Perfect for 12-factor apps:

```bash
# Set environment variables
export SWAPLAYER_PAYMENTS_PROVIDER=stripe
export SWAPLAYER_PAYMENTS_STRIPE_SECRET_KEY=sk_test_...
```

```python
# Load automatically
SWAPLAYER = SwapLayerSettings.from_env()
```

### 8. **Multi-Tenant Support**

Configure multiple apps per provider:

```python
SWAPLAYER = SwapLayerSettings(
    identity={
        'provider': 'workos',
        'workos_apps': {
            'customer_portal': {...},
            'admin_panel': {...},
            'partner_portal': {...},
        }
    }
)

# Use in code
customer_auth = get_identity_client(app_name='customer_portal')
admin_auth = get_identity_client(app_name='admin_panel')
```

## 📚 Complete Configuration Reference

### Payments Module

```python
payments={
    'provider': 'stripe',  # Only 'stripe' currently
    'stripe': {
        'secret_key': 'sk_test_...',  # Required, must start with 'sk_'
        'publishable_key': 'pk_test_...',  # Optional
        'webhook_secret': 'whsec_...',  # Optional
    }
}
```

### Email Module

```python
email={
    'provider': 'django',  # 'django' (anymail) or 'smtp'
}
# Note: Django/Anymail uses Django's EMAIL_BACKEND and ANYMAIL settings
# SMTP uses Django's EMAIL_HOST, EMAIL_PORT, etc.
```

### SMS Module

```python
sms={
    'provider': 'twilio',  # 'twilio' or 'sns'
    
    # Twilio configuration
    'twilio': {
        'account_sid': 'AC...',  # Required, must start with 'AC'
        'auth_token': '...',  # Required
        'from_number': '+15555551234',  # Required, E.164 format
    },
    
    # OR AWS SNS configuration
    'sns': {
        'aws_access_key_id': '...',  # Optional if using IAM roles
        'aws_secret_access_key': '...',  # Required if using keys
        'region_name': 'us-east-1',  # Default: 'us-east-1'
        'sender_id': 'MyApp',  # Optional
    }
}
```

### Storage Module

```python
storage={
    'provider': 'local',  # 'local' or 'django' (django-storages)
    'media_root': '/var/www/media',  # Required for local
    'media_url': '/media/',  # Default: '/media/'
}
# Note: django-storages uses DEFAULT_FILE_STORAGE and backend-specific settings
```

### Identity Platform Module

```python
identity={
    'provider': 'workos',  # 'workos' or 'auth0'
    
    # WorkOS configuration
    'workos_apps': {
        'default': {
            'api_key': 'sk_test_...',  # Required
            'client_id': 'client_...',  # Required
            'cookie_password': '...',  # Required, 32+ characters
        },
        'another_app': {...},
    },
    
    # OR Auth0 configuration
    'auth0_apps': {
        'developer': {
            'client_id': '...',  # Required
            'client_secret': '...',  # Required
        }
    },
    'auth0_domain': 'myapp.auth0.com',  # Required for Auth0
}
```

### Identity Verification Module

```python
verification={
    'provider': 'stripe',  # Only 'stripe' currently
    'stripe_secret_key': 'sk_test_...',  # Required
}
```

### Global Options

```python
SWAPLAYER = SwapLayerSettings(
    # ... module configs ...
    debug=True,  # Enable debug logging
    raise_on_error=True,  # Raise exceptions vs. return None
)
```

## 🧪 Testing

### Override in Tests

```python
# conftest.py
import pytest
from swap_layer.settings import SwapLayerSettings

@pytest.fixture
def mock_swaplayer_settings(settings):
    settings.SWAPLAYER = SwapLayerSettings(
        payments={
            'provider': 'stripe',
            'stripe': {'secret_key': 'sk_test_mock'}
        }
    )
    return settings.SWAPLAYER

def test_something(mock_swaplayer_settings):
    # Your test code
    pass
```

### Validate in Tests

```python
from swap_layer.settings import validate_swaplayer_config

def test_config_is_valid():
    result = validate_swaplayer_config()
    assert result['valid']
    assert 'payments' in result['modules']
```

## 🏭 Production Best Practices

### 1. Use Environment Variables

```python
# settings/production.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings.from_env()

# Validate on startup
from swap_layer.settings import validate_swaplayer_config
result = validate_swaplayer_config()
if not result['valid']:
    raise RuntimeError(f"SwapLayer config error: {result['error']}")
```

### 2. Separate Configs by Environment

```python
# settings/base.py
from swap_layer.settings import SwapLayerSettings

# settings/development.py
SWAPLAYER = SwapLayerSettings(
    payments={'provider': 'stripe', 'stripe': {'secret_key': 'sk_test_...'}},
    debug=True,
)

# settings/production.py
SWAPLAYER = SwapLayerSettings.from_env()
```

### 3. Health Checks

```python
# views.py
from django.http import JsonResponse
from swap_layer.settings import validate_swaplayer_config

def health_check(request):
    result = validate_swaplayer_config()
    return JsonResponse({
        'status': 'healthy' if result['valid'] else 'unhealthy',
        'swaplayer': result['modules'],
    })
```

### 4. Monitoring

```python
# apps.py
from django.apps import AppConfig
from swap_layer.settings import get_swaplayer_settings

class MyAppConfig(AppConfig):
    def ready(self):
        settings = get_swaplayer_settings()
        print(f"SwapLayer configured: {settings}")
        
        # Log to monitoring service
        logger.info("swaplayer_config", extra={
            'modules': settings.get_status()
        })
```

## 🔄 Migration from Legacy Config

If you're using the old configuration style:

```python
# OLD (still works, but migrate to new style)
PAYMENT_PROVIDER = 'stripe'
STRIPE_SECRET_KEY = 'sk_test_...'
EMAIL_PROVIDER = 'django'

# NEW (recommended)
SWAPLAYER = SwapLayerSettings(
    payments={'provider': 'stripe', 'stripe': {'secret_key': 'sk_test_...'}},
    email={'provider': 'django'},
)
```

Migration steps:
1. Add `SWAPLAYER` configuration alongside old settings
2. Test that everything works
3. Remove old settings
4. Run `python manage.py swaplayer_check` to verify

## 🤔 FAQ

**Q: Do I have to migrate to the new config?**
A: No! Legacy configuration still works. But the new system provides better validation and developer experience.

**Q: Can I use both old and new config?**
A: Yes! If `SWAPLAYER` is not found, SwapLayer automatically falls back to legacy settings.

**Q: How do I know what's required?**
A: Run `python manage.py swaplayer_check` or try to configure it - Pydantic will tell you what's missing.

**Q: Can I use this with environment variables?**
A: Yes! Use `SwapLayerSettings.from_env()` to load from `SWAPLAYER_*` environment variables.

**Q: What about secrets management?**
A: Use environment variables or your preferred secrets manager. SwapLayer just reads from Django settings.

**Q: Does this work with django-environ?**
A: Yes! Load your env vars with django-environ first, then pass them to SwapLayer.

**Q: Can I override settings in tests?**
A: Yes! See the Testing section above.

## 💡 Tips & Tricks

### Tip 1: Check config on startup
```python
# settings/production.py
from swap_layer.settings import validate_swaplayer_config

result = validate_swaplayer_config()
if not result['valid']:
    raise RuntimeError(result['error'])
```

### Tip 2: Use with django-environ
```python
import environ
from swap_layer.settings import SwapLayerSettings

env = environ.Env()

SWAPLAYER = SwapLayerSettings(
    payments={
        'provider': 'stripe',
        'stripe': {
            'secret_key': env('STRIPE_SECRET_KEY'),
            'publishable_key': env('STRIPE_PUBLISHABLE_KEY', default=None),
        }
    }
)
```

### Tip 3: Per-environment configs
```python
# Use different configs for different environments
if DEBUG:
    SWAPLAYER = SwapLayerSettings(...)
else:
    SWAPLAYER = SwapLayerSettings.from_env()
```

### Tip 4: Validate in CI/CD
```bash
# In your CI pipeline
python manage.py swaplayer_check || exit 1
```

## 🎯 Next Steps

1. ✅ Configure your first module using the new system
2. ✅ Run `python manage.py swaplayer_check` to verify
3. ✅ Update your documentation
4. ✅ Add config validation to your CI/CD pipeline
5. ✅ Migrate legacy configs over time

---

**Questions?** Check out [CONFIGURATION_EXAMPLES.md](CONFIGURATION_EXAMPLES.md) for more examples!
