# Auth0 vs WorkOS: API Comparison

## Overview

This document compares the Auth0 and WorkOS implementations in SwapLayer, highlighting key differences in API structure, capabilities, and usage patterns.

## Quick Comparison Matrix

| Feature | Auth0 | WorkOS |
|---------|-------|--------|
| **User CRUD** | ✅ Full support | ✅ Full support |
| **Organization CRUD** | ✅ Full support | ✅ Full support |
| **Role Creation** | ✅ Via API | ❌ Dashboard only |
| **Role Assignment** | ✅ Direct API | ✅ Via memberships |
| **Audit Logs** | ✅ Full access | ✅ Event API |
| **User Search** | ✅ Lucene syntax | ✅ Email filter |
| **Date Range Filtering** | ✅ Supported | ❌ Cursor-based only |
| **Individual Log Retrieval** | ✅ By ID | ❌ List only |

## User Management

### Auth0
```python
# Create user with metadata
user = mgmt.users.create_user(
    email="user@example.com",
    password="Password123!",
    email_verified=True,
    metadata={
        "department": "Engineering",
        "employee_id": "EMP001"
    }
)

# Advanced search with Lucene
results = mgmt.users.search_users(
    query='email:"*@example.com" AND metadata.department:"Engineering"'
)

# Update user metadata
mgmt.users.update_user(
    user_id=user["user_id"],
    metadata={"last_login": "2024-01-06"}
)
```

### WorkOS
```python
# Create user (metadata in root level)
user = mgmt.users.create_user(
    email="user@example.com",
    password="Password123!",
    first_name="John",
    last_name="Doe",
    email_verified=True,
    external_id="EMP001",  # For linking to your system
    metadata={"department": "Engineering"}
)

# Simple email search
results = mgmt.users.search_users(query="user@example.com")

# Update user
mgmt.users.update_user(
    user_id=user["id"],
    first_name="Jane",
    metadata={"department": "Product"}
)
```

**Key Differences:**
- Auth0 uses `user_id` field, WorkOS uses `id`
- Auth0 has advanced Lucene search, WorkOS has simple email filtering
- WorkOS has `external_id` for linking to external systems
- WorkOS separates name into `first_name`/`last_name`

## Organization Management

### Auth0
```python
# Create organization with metadata
org = mgmt.organizations.create_organization(
    name="Acme Corp",
    display_name="Acme Corporation",
    metadata={"tier": "enterprise"}
)

# Add member with roles
mgmt.organizations.add_organization_member(
    organization_id=org["id"],
    user_id=user_id,
    roles=["rol_admin", "rol_member"]
)

# Send invitation
invitation = mgmt.organizations.invite_member(
    organization_id=org["id"],
    email="newuser@acme.com",
    roles=["rol_member"],
    inviter_name="Admin User"
)
```

### WorkOS
```python
# Create organization with domains
org = mgmt.organizations.create_organization(
    name="Acme Corp",
    domains=["acme.com"],
    metadata={"tier": "enterprise"},
    external_id="ORG123"
)

# Add member with single role
mgmt.organizations.add_organization_member(
    organization_id=org["id"],
    user_id=user_id,
    role_slug="admin"  # Single role only
)

# Update member role
mgmt.organizations.update_organization_member_role(
    organization_id=org["id"],
    user_id=user_id,
    role_slug="member"
)
```

**Key Differences:**
- Auth0 supports multiple roles per member, WorkOS supports one role
- WorkOS has built-in domain management for organizations
- Auth0 has explicit invitation API, WorkOS uses membership pending state
- WorkOS uses `role_slug` (string), Auth0 uses `role IDs` (list)

## Role Management

### Auth0
```python
# Create custom role
role = mgmt.roles.create_role(
    name="Content Editor",
    description="Can create and edit content",
    permissions=[
        "read:posts",
        "write:posts",
        "read:comments",
        "write:comments"
    ]
)

# Assign role to user
mgmt.roles.assign_role_to_user(
    user_id=user_id,
    role_id=role["id"]
)

# List user's roles
user_roles = mgmt.roles.get_user_roles(user_id=user_id)

# Remove role from user
mgmt.roles.remove_role_from_user(
    user_id=user_id,
    role_id=role["id"]
)
```

### WorkOS
```python
# List organization roles (created in Dashboard)
roles = mgmt.roles.list_roles(organization_id=org_id)

# Assign role (updates membership)
mgmt.roles.assign_role_to_user(
    user_id=user_id,
    role_id="admin",  # role_slug
    organization_id=org_id  # Required!
)

# Get user's roles
user_roles = mgmt.roles.get_user_roles(
    user_id=user_id,
    organization_id=org_id
)

# Change role (update to different role)
mgmt.roles.assign_role_to_user(
    user_id=user_id,
    role_id="member",
    organization_id=org_id
)
```

**Key Differences:**
- ⚠️ Auth0 allows API role creation, WorkOS requires Dashboard
- WorkOS roles are organization-scoped (require `organization_id`)
- WorkOS doesn't support "removing" roles, only updating to different role
- Auth0 has granular permission system, WorkOS uses predefined role slugs

## Audit Logs

### Auth0
```python
# Get logs with date range
logs = mgmt.logs.filter_logs(
    start_date="2024-01-01",
    end_date="2024-01-31",
    action="s",  # Successful login
    limit=100
)

# Get specific log entry
log = mgmt.logs.get_log(log_id="90020240106...")

# Get user-specific logs
user_logs = mgmt.logs.get_user_logs(
    user_id=user_id,
    limit=50
)

# Filter by client application
app_logs = mgmt.logs.filter_logs(
    client_id="abc123",
    action="f"  # Failed login
)
```

### WorkOS
```python
# List events (cursor-based pagination)
events = mgmt.logs.list_logs(
    organization_id=org_id,
    events=["user.created", "user.updated"],
    limit=50,
    after="cursor_xyz"  # For next page
)

# Get user events (filter by type)
user_events = mgmt.logs.get_user_logs(
    user_id=user_id,
    limit=50
)

# Filter by event type
filtered_events = mgmt.logs.filter_logs(
    action="user.created"
)

# ❌ Individual event retrieval not supported
# Use list with filters instead
```

**Key Differences:**
- ⚠️ Auth0 supports date range filters, WorkOS uses cursor pagination
- ⚠️ Auth0 allows retrieving individual logs by ID, WorkOS does not
- WorkOS uses event types (e.g., `user.created`), Auth0 uses codes (e.g., `s`, `f`)
- Auth0 has more detailed log types (50+ event types)
- WorkOS events are simpler but cover core use cases

## Error Handling

### Auth0
```python
from swap_layer.identity.platform.providers.auth0.management.client import Auth0APIError

try:
    user = mgmt.users.get_user("invalid_id")
except Auth0APIError as e:
    print(f"Status: {e.status_code}")  # 404, 401, 429, etc.
    print(f"Message: {e}")
    print(f"Details: {e.details}")  # Auth0 error object
    print(f"Rate Limit: {e.rate_limit}")  # Rate limit info
```

### WorkOS
```python
from swap_layer.identity.platform.providers.workos.management import WorkOSAPIError

try:
    user = mgmt.users.get_user("invalid_id")
except WorkOSAPIError as e:
    print(f"Status: {e.status_code}")  # 404, 401, 429, etc.
    print(f"Message: {e}")
    print(f"Details: {e.details}")  # WorkOS error object
```

## API URLs

### Auth0
- **Management API Base**: `https://{domain}/api/v2/`
- **Token Endpoint**: `https://{domain}/oauth/token`
- **Users**: `/api/v2/users`
- **Organizations**: `/api/v2/organizations`
- **Roles**: `/api/v2/roles`
- **Logs**: `/api/v2/logs`

### WorkOS
- **API Base**: `https://api.workos.com`
- **Users**: `/user_management/users`
- **Organizations**: `/organizations`
- **Organization Memberships**: `/user_management/organization_memberships`
- **Roles**: `/organizations/{org_id}/roles`
- **Events**: `/events`

## Authentication

### Auth0
```python
# Machine-to-Machine (M2M) OAuth token
POST https://{domain}/oauth/token
{
    "client_id": "your_m2m_client_id",
    "client_secret": "your_m2m_client_secret",
    "audience": "https://{domain}/api/v2/",
    "grant_type": "client_credentials"
}

# Token cached and auto-refreshed by client
```

### WorkOS
```python
# API Key authentication (no token exchange needed)
Authorization: Bearer sk_your_api_key

# Simpler - no token management required
```

## Rate Limits

### Auth0
- **Read operations**: 2 requests/second (7,200/hour)
- **Write operations**: 2 requests/second (7,200/hour)
- **Search**: 2 requests/second (7,200/hour)
- Rate limit info returned in headers

### WorkOS
- **General**: 6,000 requests per 60 seconds per IP
- **User Management Reads**: 1,000 requests per 10 seconds
- **User Management Writes**: 500 requests per 10 seconds
- More lenient for most operations

## Migration Considerations

When migrating between providers:

1. **User IDs**: Auth0 uses `user_id`, WorkOS uses `id` - update your database mappings
2. **Role Assignment**: Auth0 allows multiple roles, WorkOS allows one - design accordingly
3. **Audit Logs**: Auth0 date ranges → WorkOS cursor pagination - update reporting code
4. **Role Management**: WorkOS roles created in Dashboard, not API - pre-create roles
5. **Organization Domains**: WorkOS has built-in domain support - leverage it
6. **External IDs**: WorkOS has `external_id` field - use for linking to your system

## Recommendation

- **Use Auth0 if you need**:
  - Programmatic role creation
  - Advanced search capabilities
  - Multiple roles per user
  - Date-range log filtering
  
- **Use WorkOS if you need**:
  - Simpler API authentication (API key)
  - Built-in organization domain management
  - Modern cursor-based pagination
  - Better documentation and developer experience

Both are excellent choices - the best fit depends on your specific requirements!
