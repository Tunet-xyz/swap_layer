# SwapLayer Module Standardization

Every SwapLayer module now follows a consistent structure for effortless developer experience.

## ✅ What Every Module Has

### 1. Files Structure

```
swap_layer/{module}/
├── __init__.py          # Exports get_provider() + adapter
├── adapter.py           # Abstract base class (ABC)
├── factory.py           # get_{module}_provider() function
├── models.py            # Django model mixins
├── admin.py             # Django admin mixins
├── apps.py              # Django AppConfig
├── README.md            # Complete documentation
├── providers/           # Provider implementations
│   ├── __init__.py
│   └── {provider}.py    # e.g., stripe.py, twilio.py
```

### 2. Import Pattern (STANDARDIZED)

Every module supports both specific and generic imports:

```python
# Method 1: Module-specific (explicit)
from swap_layer.payments import get_provider
payments = get_provider()

# Method 2: Top-level (unified)
from swap_layer import get_provider
payments = get_provider('payments')

# Method 3: Factory function (direct)
from swap_layer.payments.factory import get_payment_provider
payments = get_payment_provider()
```

**All three methods work identically.** Choose based on your preference.

### 3. Django Integration (STANDARDIZED)

Every module provides:

#### A. Django Settings Configuration
```python
# settings.py
INSTALLED_APPS = [
    'swap_layer.payments.apps.PaymentsConfig',
    'swap_layer.email.apps.EmailConfig',
    'swap_layer.storage.apps.StorageConfig',
    'swap_layer.sms.apps.SmsConfig',
    'swap_layer.identity.platform.apps.IdentityPlatformConfig',
    'swap_layer.identity.verification.apps.IdentityVerificationConfig',
]

# Provider selection
PAYMENT_PROVIDER = 'stripe'
EMAIL_PROVIDER = 'django'
STORAGE_PROVIDER = 's3'
SMS_PROVIDER = 'twilio'
IDENTITY_PROVIDER = 'workos'
IDENTITY_VERIFICATION_PROVIDER = 'stripe'
```

#### B. Model Mixins
```python
# Available for all modules
from swap_layer.payments.models import PaymentProviderCustomerMixin
from swap_layer.email.models import EmailLogMixin
from swap_layer.storage.models import StorageFileMixin
from swap_layer.sms.models import SMSMessageMixin
from swap_layer.identity.platform.models import OAuthIdentityMixin
from swap_layer.identity.verification.models import IdentityVerificationMixin
```

#### C. Admin Integrations
```python
# Available for all modules
from swap_layer.payments.admin import PaymentProviderAdminMixin
from swap_layer.email.admin import EmailLogAdminMixin
from swap_layer.storage.admin import StorageFileAdminMixin
from swap_layer.sms.admin import SMSMessageAdminMixin
from swap_layer.identity.platform.admin import OAuthIdentityAdminMixin
from swap_layer.identity.verification.admin import IdentityVerificationAdminMixin
```

### 4. README Structure (STANDARDIZED)

Every module README follows this template:

1. **Title & Description** - What the module does
2. **Architecture** - Diagram of adapter pattern
3. **Features** - Bullet list of capabilities
4. **Installation** - INSTALLED_APPS + pip install
5. **Configuration** - Django settings examples
6. **Usage Examples** - Common operations with code
7. **API Reference** - All adapter methods documented
8. **Provider Comparison** - Feature matrix by provider
9. **Django Integration** - Model mixins, admin, commands
10. **Error Handling** - Exception types
11. **Best Practices** - Security, performance tips
12. **Advanced** - Webhooks, async (future), testing

---

## Module Checklist

| Module | __init__ | models.py | admin.py | README | Django Integration Section |
|--------|----------|-----------|----------|--------|---------------------------|
| ✅ **payments** | ✅ | ✅ | ✅ | ✅ | ✅ |
| ✅ **email** | ✅ | ✅ | ✅ | ✅ | Needs update |
| ✅ **storage** | ✅ | ✅ | ✅ | ✅ | Needs update |
| ✅ **sms** | ✅ | ✅ | ✅ | ✅ | Needs update |
| ✅ **identity/platform** | ✅ | ✅ | ✅ | ✅ | Needs update |
| ✅ **identity/verification** | ✅ | ✅ | ✅ | ✅ | Needs update |

---

## Usage Examples (Standardized Across All Modules)

### Payments
```python
from swap_layer import get_provider

payments = get_provider('payments')
customer = payments.create_customer(email='user@example.com')
```

### Email
```python
from swap_layer import get_provider

email = get_provider('email')
email.send_email(
    to=['user@example.com'],
    subject='Welcome!',
    body='Thanks for signing up'
)
```

### Storage
```python
from swap_layer import get_provider

storage = get_provider('storage')
storage.upload_file('avatar.jpg', file_obj, content_type='image/jpeg')
```

### SMS
```python
from swap_layer import get_provider

sms = get_provider('sms')
sms.send_sms(to='+1234567890', message='Your code is 123456')
```

### Identity (OAuth/OIDC)
```python
from swap_layer import get_provider

identity = get_provider('identity')
url = identity.get_authorization_url(redirect_uri='...')
```

### Identity Verification (KYC)
```python
from swap_layer import get_provider

verification = get_provider('verification')
session = verification.create_verification_session(...)
```

---

## Benefits of Standardization

1. **Predictable**: Same pattern across all 6 modules
2. **Flexible**: Three import styles (module, unified, factory)
3. **Django-first**: Models, admin, commands for every domain
4. **Documented**: Every README follows same structure
5. **Discoverable**: Consistent naming (get_provider everywhere)
6. **Testable**: Consistent mocking points
7. **Maintainable**: Easy to add new modules following pattern

---

## For Contributors: Adding a New Module

To add a new module (e.g., `swap_layer/analytics/`):

1. **Create structure**:
   ```
   analytics/
   ├── __init__.py          # Export get_provider
   ├── adapter.py           # AnalyticsProviderAdapter (ABC)
   ├── factory.py           # get_analytics_provider()
   ├── models.py            # Django mixins
   ├── admin.py             # Django admin
   ├── apps.py              # AnalyticsConfig
   ├── README.md
   └── providers/
       └── google_analytics.py
   ```

2. **Update top-level `__init__.py`**:
   ```python
   from .analytics.factory import get_analytics_provider
   
   def get_provider(service_type: str, **kwargs):
       # Add case
       elif service == 'analytics':
           return get_analytics_provider()
   ```

3. **Follow README template** from any existing module

4. **Add tests** following `tests/test_{module}.py` pattern

5. **Update** this standardization doc with new module

---

## Verification

Run this to verify standardization:

```bash
# Check all modules have required files
ls src/swap_layer/*/models.py
ls src/swap_layer/*/admin.py
ls src/swap_layer/*/README.md

# Test unified import
python -c "from swap_layer import get_provider; print('✓ Unified import works')"

# Test module imports
python -c "from swap_layer.payments import get_provider; print('✓ Module imports work')"
```

---

**Every module. Same pattern. Zero confusion.**
