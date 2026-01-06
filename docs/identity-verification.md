# Identity Verification

Provider-agnostic identity verification (KYC) abstraction layer for integrating document verification and identity checks using Stripe Identity, Onfido, and other providers.

## Overview

This module provides a unified interface for identity verification services, allowing you to implement KYC (Know Your Customer) checks and document verification without being locked into a specific provider.

## Architecture

```
swap_layer/identity/verification/
├── __init__.py
├── adapter.py                 # IdentityVerificationProviderAdapter (ABC)
├── factory.py                 # get_identity_verification_provider() factory
├── apps.py                    # Django AppConfig
├── models.py                  # IdentityVerificationSession data model
├── schemas.py                 # Pydantic schemas for validation
├── repository.py              # Data persistence abstraction
├── services.py                # High-level service layer
├── frameworks/                # Framework integrations
│   └── django.py              # Django model & repository
├── operations/                # Business logic
│   ├── __init__.py
│   └── core.py                # Core verification operations
└── providers/                 # Provider implementations
    ├── __init__.py
    └── stripe.py              # Stripe Identity implementation

```

## Features

- **Document Verification**: Verify government-issued IDs (passport, driver's license, etc.)
- **Session Management**: Create and manage verification sessions
- **Status Tracking**: Track verification progress (pending, verified, failed)
- **Report Retrieval**: Get detailed verification reports
- **Webhook Support**: Process verification status updates
- **Verified Data Extraction**: Extract verified user information (name, DOB, address)
- **Database Persistence**: Optional Django ORM integration

## Configuration

Add to your Django `settings.py`:

```python
# Identity Verification Provider Selection
IDENTITY_VERIFICATION_PROVIDER = 'stripe'  # Options: 'stripe', 'onfido' (coming soon)

# Stripe Identity Configuration (if using Stripe)
STRIPE_SECRET_KEY = 'sk_live_...'
STRIPE_IDENTITY_WEBHOOK_SECRET = 'whsec_...'

# Optional: Custom Django model for persistence
SWAP_LAYER_VERIFICATION_MODEL = 'myapp.IdentityVerification'
```

**Security:** Use environment variables:

```python
import os
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'swap_layer.identity.verification.apps.IdentityVerificationConfig',
    # ...
]
```

## Usage Examples

### Basic Verification Flow

```python
from swap_layer.identity.verification.factory import get_identity_verification_provider

# Initialize provider
provider = get_identity_verification_provider()

# Create verification session
session = provider.create_verification_session(
    user=request.user,
    verification_type='document',
    options={
        'return_url': 'https://example.com/verification/complete'
    }
)

# Redirect user to verification URL
return redirect(session['url'])

# Later, check verification status
status = provider.get_verification_session(session['provider_session_id'])
if status['status'] == 'verified':
    # Extract verified data
    verified_data = status['verified_outputs']
    user.first_name = verified_data.get('first_name')
    user.last_name = verified_data.get('last_name')
    user.save()
```

### Django View Example

```python
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from swap_layer.identity.verification.factory import get_identity_verification_provider

@login_required
def start_verification(request):
    """Initiate identity verification"""
    provider = get_identity_verification_provider()
    
    # Create verification session
    session = provider.create_verification_session(
        user=request.user,
        verification_type='document',
        options={
            'return_url': request.build_absolute_uri('/verification/complete')
        }
    )
    
    # Store session ID in user session for later retrieval
    request.session['verification_session_id'] = session['provider_session_id']
    
    # Redirect to provider's verification page
    return redirect(session['url'])

@login_required
def verification_complete(request):
    """Handle verification completion callback"""
    session_id = request.session.get('verification_session_id')
    if not session_id:
        return redirect('start_verification')
    
    provider = get_identity_verification_provider()
    
    # Retrieve verification session
    session = provider.get_verification_session(session_id)
    
    if session['status'] == 'verified':
        # Update user profile with verified data
        verified = session.get('verified_outputs', {})
        request.user.profile.identity_verified = True
        request.user.profile.verified_first_name = verified.get('first_name')
        request.user.profile.verified_last_name = verified.get('last_name')
        request.user.profile.save()
        
        return render(request, 'verification_success.html')
    elif session['status'] == 'requires_input':
        # User needs to complete verification
        return redirect(session['url'])
    else:
        # Verification failed or cancelled
        return render(request, 'verification_failed.html', {
            'error': session.get('last_error')
        })
```

### Webhook Handler

```python
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from swap_layer.identity.verification.factory import get_identity_verification_provider
import json

@csrf_exempt
def verification_webhook(request):
    """Handle verification status updates from provider"""
    provider = get_identity_verification_provider()
    
    payload = request.body
    signature = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        # Verify webhook signature
        event = provider.verify_webhook_signature(
            payload=payload,
            signature=signature,
            webhook_secret=settings.STRIPE_IDENTITY_WEBHOOK_SECRET
        )
        
        # Handle different event types
        if event['type'] == 'identity.verification_session.verified':
            session = event['data']
            # Update user verification status
            handle_verification_success(session)
        elif event['type'] == 'identity.verification_session.requires_input':
            # User needs to retry
            handle_verification_retry(event['data'])
        
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        return HttpResponse(str(e), status=400)
```

### Using the Service Layer (with Database Persistence)

```python
from swap_layer.identity.verification.services import VerificationService
from swap_layer.identity.verification.schemas import VerificationSessionCreate

# Initialize service (handles database persistence)
service = VerificationService()

# Create verification session
session_data = VerificationSessionCreate(
    verification_type='document',
    return_url='https://example.com/callback'
)

session = service.create_verification_session(
    user=request.user,
    session_data=session_data
)

# Session is automatically saved to database
# Retrieve later from database
saved_session = service.get_session_by_id(session.id)
```

### Custom Django Model Integration

```python
# models.py
from swap_layer.identity.verification.frameworks.django import AbstractIdentityVerificationSession

class IdentityVerification(AbstractIdentityVerificationSession):
    """Custom verification model with additional fields"""
    
    # Add custom fields
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        db_table = 'identity_verifications'
        verbose_name = 'Identity Verification'
        verbose_name_plural = 'Identity Verifications'

# settings.py
SWAP_LAYER_VERIFICATION_MODEL = 'myapp.IdentityVerification'
```

## Provider Comparison

| Feature | Stripe Identity | Onfido | Status |
|---------|----------------|--------|--------|
| **Document Verification** | ✅ | 🚧 | Stripe implemented |
| **Selfie Verification** | ✅ | 🚧 | Stripe implemented |
| **Address Verification** | ✅ | 🚧 | Stripe implemented |
| **Session Management** | ✅ | 🚧 | Stripe implemented |
| **Webhooks** | ✅ | 🚧 | Stripe implemented |
| **Report Retrieval** | ✅ | 🚧 | Stripe implemented |
| **Live Check** | ❌ | 🚧 | Onfido specialty |
| **Video Verification** | ❌ | 🚧 | Onfido specialty |

✅ = Fully implemented | ❌ = Not supported | 🚧 = Planned

## Normalized Data Format

All providers return session data in this standardized format:

```python
{
    'provider_session_id': 'vs_1ABC...',
    'user_id': 123,
    'status': 'verified',                      # requires_input, processing, verified, failed
    'verification_type': 'document',
    'provider': 'stripe',
    'client_secret': 'vs_1ABC_secret_XYZ',
    'url': 'https://verify.stripe.com/...',    # Where user goes to verify
    'metadata': {},
    'verification_report_id': 'vr_1ABC...',
    'verified_at': datetime(...),              # When verification completed
    'verified_outputs': {                      # Extracted verified data
        'first_name': 'John',
        'last_name': 'Doe',
        'dob': '1990-01-01',
        'id_number': 'ABC123',
        'address': {...}
    },
    'last_error': None                         # Error message if failed
}
```

## Benefits

1. **Provider Independence**: Switch between Stripe, Onfido, or custom providers with one config change
2. **Regulatory Compliance**: Meet KYC requirements across jurisdictions
3. **Easy Testing**: Mock the adapter interface for testing without real verifications
4. **Type Safety**: Full type hints with Pydantic schemas
5. **Database Integration**: Optional Django ORM persistence
6. **No Vendor Lock-in**: Avoid dependency on a single verification platform

## Adding a New Provider

To add a new verification provider (e.g., Onfido):

1. Create `swap_layer/identity/verification/providers/onfido.py`:

```python
from swap_layer.identity.verification.adapter import IdentityVerificationProviderAdapter

class OnfidoIdentityVerificationProvider(IdentityVerificationProviderAdapter):
    def __init__(self):
        # Initialize Onfido SDK
        pass
    
    def create_verification_session(self, user, verification_type, options=None):
        # Create Onfido applicant and check
        # Return normalized session data
        pass
    
    def get_verification_session(self, session_id):
        # Retrieve check status from Onfido
        # Return normalized session data
        pass
    
    # Implement all abstract methods...
```

2. Update `factory.py`:

```python
def get_identity_verification_provider():
    provider = getattr(settings, 'IDENTITY_VERIFICATION_PROVIDER', 'stripe')
    
    if provider == 'onfido':
        from .providers.onfido import OnfidoIdentityVerificationProvider
        return OnfidoIdentityVerificationProvider()
    # ... existing providers
```

3. Add configuration:

```python
IDENTITY_VERIFICATION_PROVIDER = 'onfido'
ONFIDO_API_TOKEN = os.environ.get('ONFIDO_API_TOKEN')
ONFIDO_WEBHOOK_TOKEN = os.environ.get('ONFIDO_WEBHOOK_TOKEN')
```

## Testing

```python
from unittest.mock import Mock
from swap_layer.identity.verification.adapter import IdentityVerificationProviderAdapter

def test_verification():
    # Mock the provider
    mock_provider = Mock(spec=IdentityVerificationProviderAdapter)
    mock_provider.create_verification_session.return_value = {
        'provider_session_id': 'vs_test_123',
        'status': 'requires_input',
        'url': 'https://test.com/verify',
        'client_secret': 'test_secret'
    }
    
    # Test your code
    session = mock_provider.create_verification_session(
        user=mock_user,
        verification_type='document'
    )
    
    assert session['status'] == 'requires_input'
```

## Related Modules

- **Identity Platform**: `swap_layer/identity/platform/` - OAuth authentication (WorkOS, Auth0)
- **Payments**: `swap_layer/payments/` - Link verified identity to payment accounts
- **Email**: `swap_layer/email/` - Send verification status notifications

## License

This module is part of the SwapLayer project.
