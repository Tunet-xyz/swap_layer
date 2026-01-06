# Identity Platform (Authentication)

Provider-agnostic authentication abstraction layer for integrating third-party identity providers like WorkOS, Auth0, and others without vendor lock-in.

## Overview

This module provides a unified interface for OAuth/OIDC authentication providers, allowing you to switch between WorkOS, Auth0, and other identity platforms without changing your application code.

## Architecture

```
swap_layer/identity/platform/
├── __init__.py
├── adapter.py                 # AuthProviderAdapter (ABC)
├── factory.py                 # get_identity_client() factory
├── apps.py                    # Django AppConfig
├── models.py                  # Data models
├── operations.py              # Business logic
├── repository.py              # Data persistence
├── services.py                # High-level service layer
├── frameworks/                # Framework integrations
│   └── django.py              # Django-specific helpers
└── providers/                 # Provider implementations
    ├── auth0/
    │   └── client.py          # Auth0 implementation
    └── workos/
        ├── __init__.py
        └── client.py          # WorkOS implementation

```

## Features

- **OAuth/OIDC Flow**: Complete authorization code flow
- **Authorization URL Generation**: Redirect users to provider login
- **Code Exchange**: Exchange authorization codes for user data
- **Logout URL Generation**: Provider-specific logout URLs
- **Multi-App Support**: Support multiple applications per provider
- **Normalized User Data**: Consistent user data format across providers

## Configuration

Add to your Django `settings.py`:

```python
# Identity Provider Selection
IDENTITY_PROVIDER = 'workos'  # Options: 'workos', 'auth0'

# WorkOS Configuration (if using WorkOS)
WORKOS_API_KEY = 'sk_live_...'
WORKOS_CLIENT_ID = 'client_...'

# Auth0 Configuration (if using Auth0)
AUTH0_DOMAIN = 'myapp.us.auth0.com'
AUTH0_CLIENT_ID = '...'
AUTH0_CLIENT_SECRET = '...'
```

**Security:** Use environment variables for secrets:

```python
import os
WORKOS_API_KEY = os.environ.get('WORKOS_API_KEY')
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    'swap_layer.identity.platform.apps.IdentityPlatformConfig',
    # ...
]
```

## Usage Examples

### Basic OAuth Flow

```python
from swap_layer.identity.platform.factory import get_identity_client

# Initialize the provider
identity = get_identity_client(app_name='default')

# Step 1: Generate authorization URL
auth_url = identity.get_authorization_url(
    request=request,
    redirect_uri='https://example.com/auth/callback',
    state='random_state_value'
)
# Redirect user to auth_url

# Step 2: Handle callback
def callback_view(request):
    code = request.GET.get('code')
    
    # Exchange code for user data
    user_data = identity.exchange_code_for_user(request, code)
    
    # user_data contains:
    # {
    #     'id': 'user_01...',
    #     'email': 'user@example.com',
    #     'first_name': 'John',
    #     'last_name': 'Doe',
    #     'profile': {...}
    # }
    
    # Create or update user in your database
    user = User.objects.get_or_create(email=user_data['email'])
    # ... handle login
```

### Django Integration

```python
from django.shortcuts import redirect
from django.http import HttpResponse
from swap_layer.identity.platform.factory import get_identity_client
import secrets

def login_view(request):
    """Initiate OAuth login"""
    identity = get_identity_client()
    
    # Generate and store state for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state
    
    # Get authorization URL
    auth_url = identity.get_authorization_url(
        request=request,
        redirect_uri=request.build_absolute_uri('/auth/callback'),
        state=state
    )
    
    return redirect(auth_url)

def callback_view(request):
    """Handle OAuth callback"""
    # Verify state
    if request.GET.get('state') != request.session.get('oauth_state'):
        return HttpResponse('Invalid state', status=400)
    
    code = request.GET.get('code')
    if not code:
        return HttpResponse('No code provided', status=400)
    
    # Exchange code for user
    identity = get_identity_client()
    try:
        user_data = identity.exchange_code_for_user(request, code)
        
        # Create or get user
        user, created = User.objects.get_or_create(
            email=user_data['email'],
            defaults={
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', ''),
            }
        )
        
        # Log user in
        login(request, user)
        return redirect('dashboard')
        
    except Exception as e:
        return HttpResponse(f'Authentication failed: {str(e)}', status=400)

def logout_view(request):
    """Handle logout with provider"""
    identity = get_identity_client()
    
    # Logout from Django
    logout(request)
    
    # Get provider logout URL
    logout_url = identity.get_logout_url(
        request=request,
        return_to=request.build_absolute_uri('/')
    )
    
    return redirect(logout_url)
```

### Multi-Application Support

```python
# Configure multiple applications
identity_app1 = get_identity_client(app_name='consumer_app')
identity_app2 = get_identity_client(app_name='business_app')

# Each can have different settings
auth_url_1 = identity_app1.get_authorization_url(request, ...)
auth_url_2 = identity_app2.get_authorization_url(request, ...)
```

## Provider Comparison

| Feature | WorkOS | Auth0 | Status |
|---------|--------|-------|--------|
| **OAuth/OIDC** | ✅ | ✅ | Implemented |
| **Authorization URL** | ✅ | ✅ | Implemented |
| **Code Exchange** | ✅ | ✅ | Implemented |
| **Logout URL** | ✅ | ✅ | Implemented |
| **Multi-App Support** | ✅ | ✅ | Implemented |
| **SSO (Enterprise)** | ✅ | ✅ | Provider-dependent |
| **MFA** | ✅ | ✅ | Provider-dependent |

## Normalized Data Format

All providers return user data in this standardized format:

```python
{
    'id': 'user_01ABC...',           # Provider-specific user ID
    'email': 'user@example.com',      # Email address
    'email_verified': True,           # Email verification status
    'first_name': 'John',             # First name (optional)
    'last_name': 'Doe',               # Last name (optional)
    'profile': {                      # Provider-specific profile data
        'picture': 'https://...',
        'locale': 'en-US',
        # ... other provider fields
    }
}
```

## Benefits

1. **Provider Independence**: Switch between WorkOS, Auth0, or custom providers with one config change
2. **Consistent Interface**: Same API regardless of identity provider
3. **Easy Testing**: Mock the adapter interface for unit tests
4. **Type Safety**: Full type hints for better IDE support
5. **No Vendor Lock-in**: Avoid dependency on a single identity platform
6. **Enterprise Ready**: Support SSO, MFA, and other enterprise features

## Adding a New Provider

To add a new identity provider (e.g., Supabase):

1. Create `swap_layer/identity/platform/providers/supabase/client.py`:

```python
from swap_layer.identity.platform.adapter import AuthProviderAdapter

class SupabaseClient(AuthProviderAdapter):
    def __init__(self, app_name='default'):
        # Initialize Supabase client
        pass
    
    def get_authorization_url(self, request, redirect_uri, state=None):
        # Implement Supabase OAuth URL generation
        pass
    
    def exchange_code_for_user(self, request, code):
        # Exchange code for user data
        # Return normalized user data
        pass
    
    def get_logout_url(self, request, return_to):
        # Implement logout URL
        pass
```

2. Update `factory.py`:

```python
def get_identity_client(app_name='default') -> AuthProviderAdapter:
    provider = getattr(settings, 'IDENTITY_PROVIDER', 'workos')
    
    if provider == 'supabase':
        from .providers.supabase.client import SupabaseClient
        return SupabaseClient(app_name=app_name)
    # ... existing providers
```

3. Add configuration:

```python
IDENTITY_PROVIDER = 'supabase'
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
```

## Testing

```python
from unittest.mock import Mock
from swap_layer.identity.platform.adapter import AuthProviderAdapter

def test_oauth_flow():
    # Mock the provider
    mock_identity = Mock(spec=AuthProviderAdapter)
    mock_identity.get_authorization_url.return_value = 'https://provider.com/oauth'
    mock_identity.exchange_code_for_user.return_value = {
        'id': 'user_123',
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User'
    }
    
    # Test your code with the mock
    url = mock_identity.get_authorization_url(request, redirect_uri='...')
    assert 'https://provider.com' in url
```

## Migration from Direct Provider Usage

### Before (Direct WorkOS usage):

```python
import workos
workos.api_key = settings.WORKOS_API_KEY
workos_client = workos.client.WorkOSClient()
authorization_url = workos_client.sso.get_authorization_url(...)
```

### After (Using abstraction):

```python
from swap_layer.identity.platform.factory import get_identity_client
identity = get_identity_client()
authorization_url = identity.get_authorization_url(...)
```

## Related Modules

- **Identity Verification**: `swap_layer/identity/verification/` - KYC/identity verification (Stripe Identity, Onfido)
- **Email**: `swap_layer/email/` - Send verification emails
- **Payments**: `swap_layer/payments/` - Link identity to payment customers

## License

This module is part of the SwapLayer project.
