# Identity Management API

Provider-agnostic abstraction for identity management operations (user management, organizations, roles, audit logs).

## Overview

This module provides administrative operations for identity providers. It is **separate from authentication** (OAuth/OIDC) which is handled by the `identity.platform` module.

**Key Concepts:**
- **Authentication** (`identity.platform`): User login/logout via OAuth/OIDC
- **Management** (`identity.platform.management`): Administrative operations (CRUD users, manage organizations, assign roles)

## Architecture

```
identity/platform/management/
├── adapter.py              # Abstract base classes (ABCs)
├── factory.py              # get_management_client()
└── __init__.py

providers/auth0/management/
├── client.py               # Auth0ManagementClient (composes modules)
├── users.py                # Auth0UserManagement
├── organizations.py        # Auth0OrganizationManagement
├── roles.py                # Auth0RoleManagement
├── logs.py                 # Auth0LogManagement
└── __init__.py

providers/workos/
└── management.py           # WorkOSManagementClient (stub - to be implemented)
```

### Abstraction Layers

The management API is split into four key adapters:

1. **UserManagementAdapter**: User CRUD operations
2. **OrganizationManagementAdapter**: Organization/tenant management
3. **RoleManagementAdapter**: Role and permission assignment
4. **LogManagementAdapter**: Audit logs and events

Each provider implements these adapters, allowing you to switch providers without changing your code.

## Installation

Add to `INSTALLED_APPS` in Django settings:

```python
INSTALLED_APPS = [
    # ...
    'swap_layer.identity.platform.apps.IdentityPlatformConfig',
]
```

## Configuration

### Auth0 Configuration

```python
# settings.py

IDENTITY_PROVIDER = 'auth0'
AUTH0_DEVELOPER_DOMAIN = 'yourapp.us.auth0.com'

AUTH0_APPS = {
    'default': {
        # OAuth credentials (for user authentication)
        'client_id': os.environ['AUTH0_CLIENT_ID'],
        'client_secret': os.environ['AUTH0_CLIENT_SECRET'],
        
        # Management API credentials (for administrative operations)
        # Create a "Machine to Machine" application in Auth0 Dashboard
        # and authorize it for the Auth0 Management API
        'management_client_id': os.environ['AUTH0_MGMT_CLIENT_ID'],
        'management_client_secret': os.environ['AUTH0_MGMT_CLIENT_SECRET'],
    }
}
```

**Setting up Auth0 Management API:**

1. Go to Auth0 Dashboard → Applications
2. Create a new "Machine to Machine" application
3. Authorize it to use the "Auth0 Management API"
4. Select the scopes you need:
   - `read:users`, `create:users`, `update:users`, `delete:users`
   - `read:organizations`, `create:organizations`, `update:organizations`
   - `read:roles`, `create:roles`, `update:roles`
   - `read:logs`
5. Copy the Client ID and Client Secret

### WorkOS Configuration

```python
# settings.py

IDENTITY_PROVIDER = 'workos'
WORKOS_APPS = {
    'default': {
        'api_key': os.environ['WORKOS_API_KEY'],
        'client_id': os.environ['WORKOS_CLIENT_ID'],
        'cookie_password': os.environ['WORKOS_COOKIE_PASSWORD'],
    }
}
```

Note: WorkOS management implementation is currently a stub and needs to be completed.

## Usage

### Basic Usage

```python
from swap_layer.identity.platform.management.factory import get_management_client

# Get management client (provider-agnostic)
mgmt = get_management_client(app_name='default')

# The client has four modules
mgmt.users         # User management operations
mgmt.organizations # Organization management operations
mgmt.roles         # Role and permission management
mgmt.logs          # Audit log access
```

### User Management

```python
mgmt = get_management_client()

# List users
users = mgmt.users.list_users(page=0, per_page=50)

# Search users (provider-specific query syntax)
users = mgmt.users.search_users(
    query='email:"*@example.com"',
    per_page=50
)

# Get specific user
user = mgmt.users.get_user(user_id='auth0|123')

# Create user
user = mgmt.users.create_user(
    email='new@example.com',
    password='SecurePass123!',
    email_verified=False,
    metadata={'tier': 'free', 'source': 'admin_invite'}
)

# Update user
user = mgmt.users.update_user(
    user_id='auth0|123',
    email='updated@example.com',
    metadata={'tier': 'premium'}
)

# Delete user
mgmt.users.delete_user(user_id='auth0|123')
```

### Organization Management

```python
mgmt = get_management_client()

# List organizations
orgs = mgmt.organizations.list_organizations(page=0, per_page=50)

# Get organization
org = mgmt.organizations.get_organization(org_id='org_abc123')

# Create organization
org = mgmt.organizations.create_organization(
    name='acme-corp',
    display_name='ACME Corporation',
    metadata={'industry': 'Technology', 'plan': 'enterprise'}
)

# Update organization
org = mgmt.organizations.update_organization(
    org_id='org_abc123',
    display_name='ACME Corp International',
    metadata={'employee_count': 500}
)

# Delete organization
mgmt.organizations.delete_organization(org_id='org_abc123')

# List organization members
members = mgmt.organizations.list_organization_members(
    org_id='org_abc123',
    page=0,
    per_page=50
)

# Add members to organization
mgmt.organizations.add_organization_members(
    org_id='org_abc123',
    user_ids=['auth0|123', 'auth0|456']
)

# Remove members from organization
mgmt.organizations.remove_organization_members(
    org_id='org_abc123',
    user_ids=['auth0|789']
)
```

### Role Management

```python
mgmt = get_management_client()

# List all roles
roles = mgmt.roles.list_roles(page=0, per_page=50)

# Get role details
role = mgmt.roles.get_role(role_id='rol_abc123')

# Get user's roles
user_roles = mgmt.roles.get_user_roles(user_id='auth0|123')

# Assign roles to user
mgmt.roles.assign_user_roles(
    user_id='auth0|123',
    role_ids=['rol_admin', 'rol_editor']
)

# Remove roles from user
mgmt.roles.remove_user_roles(
    user_id='auth0|123',
    role_ids=['rol_viewer']
)

# Get user's effective permissions
permissions = mgmt.roles.get_user_permissions(user_id='auth0|123')
```

### Audit Logs

```python
mgmt = get_management_client()

# List all logs
logs = mgmt.logs.list_logs(page=0, per_page=50)

# Filter logs with query (provider-specific syntax)
# Auth0 uses Lucene query syntax
logs = mgmt.logs.list_logs(
    query='type:f AND date:[2024-01-01 TO 2024-12-31]',
    per_page=100
)

# Get specific log entry
log = mgmt.logs.get_log(log_id='log_123')

# Get logs for specific user
user_logs = mgmt.logs.get_user_logs(
    user_id='auth0|123',
    page=0,
    per_page=50
)
```

## Django View Examples

### Admin User List

```python
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from swap_layer.identity.platform.management.factory import get_management_client

@staff_member_required
def admin_users_list(request):
    mgmt = get_management_client()
    
    users = mgmt.users.list_users(
        page=int(request.GET.get('page', 0)),
        per_page=int(request.GET.get('per_page', 50)),
        search_query=request.GET.get('q')
    )
    
    return JsonResponse({'users': users})
```

### Create User with Organization and Role

```python
@staff_member_required
def admin_create_user_complete(request):
    import json
    data = json.loads(request.body)
    
    mgmt = get_management_client()
    
    # 1. Create user
    user = mgmt.users.create_user(
        email=data['email'],
        password=data['password'],
        metadata={'created_by': 'admin'}
    )
    
    # 2. Add to organization
    if org_id := data.get('organization_id'):
        mgmt.organizations.add_organization_members(
            org_id=org_id,
            user_ids=[user['user_id']]
        )
    
    # 3. Assign roles
    if role_ids := data.get('role_ids'):
        mgmt.roles.assign_user_roles(
            user_id=user['user_id'],
            role_ids=role_ids
        )
    
    return JsonResponse(user, status=201)
```

## Provider-Specific Operations

Sometimes you need provider-specific features that aren't in the abstraction. You can access the provider-specific client directly:

```python
from swap_layer.identity.platform.providers.auth0.management import Auth0ManagementClient

# Use Auth0-specific client
mgmt = Auth0ManagementClient(app_name='default')

# Auth0-specific operations
role_permissions = mgmt.roles.get_role_permissions(role_id='rol_abc')
mgmt.roles.add_role_permissions(
    role_id='rol_abc',
    permissions=[
        {
            'resource_server_identifier': 'api.example.com',
            'permission_name': 'read:users'
        }
    ]
)
```

## Switching Providers

To switch from Auth0 to WorkOS (or vice versa), just change the configuration:

```python
# From Auth0
IDENTITY_PROVIDER = 'auth0'

# To WorkOS
IDENTITY_PROVIDER = 'workos'
```

Your code using `get_management_client()` will work with either provider!

## Benefits

1. **Provider Independence**: Switch between Auth0, WorkOS, or custom providers with config change
2. **Modular Design**: Each concern (users, orgs, roles, logs) is a separate module
3. **Consistent Interface**: Same API regardless of identity provider
4. **Easy Testing**: Mock the adapter interfaces for unit tests
5. **Type Safety**: Full type hints for better IDE support
6. **No Vendor Lock-in**: Avoid dependency on a single identity platform
7. **Composable**: Use only the modules you need
8. **Maintainable**: Clear separation makes it easy to extend

## Comparison with Authentication

| Feature | Authentication Module | Management Module |
|---------|----------------------|-------------------|
| **Purpose** | User login/logout | Administrative operations |
| **Scope** | Single authenticated user | All tenant data |
| **Operations** | OAuth flow, token exchange | CRUD users, manage orgs |
| **API** | OAuth/OIDC endpoints | Management API |
| **Token** | Access token for user | Management API token |
| **Use Case** | "Log me in" | "Create a user", "Assign role" |
| **Factory** | `get_identity_client()` | `get_management_client()` |

## Testing

```python
import unittest
from unittest.mock import Mock
from swap_layer.identity.platform.management.adapter import UserManagementAdapter

def test_user_management():
    # Mock the adapter
    mock_mgmt = Mock()
    mock_mgmt.users = Mock(spec=UserManagementAdapter)
    mock_mgmt.users.list_users.return_value = [
        {'user_id': 'user_123', 'email': 'test@example.com'}
    ]
    
    # Test your code
    users = mock_mgmt.users.list_users()
    assert len(users) == 1
    assert users[0]['email'] == 'test@example.com'
```

## Related Modules

- **Authentication**: `swap_layer.identity.platform` - OAuth/OIDC authentication
- **Identity Verification**: `swap_layer.identity.verification` - KYC/identity verification
- **Email**: `swap_layer.communications.email` - Send notification emails
- **Billing**: `swap_layer.billing` - Link users to billing customers

## License

This module is part of the SwapLayer project.
