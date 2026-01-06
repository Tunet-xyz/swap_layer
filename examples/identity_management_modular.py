"""
Identity Management Usage Examples

Demonstrates the modular architecture for identity management operations.

Architecture:
    - Authentication (OAuth/OIDC): identity.platform.factory.get_identity_client()
    - Management (Admin Ops): identity.platform.management.factory.get_management_client()
    
    Management is split into modules:
        - users: User CRUD operations
        - organizations: Organization/tenant management
        - roles: Role and permission assignment
        - logs: Audit logs and events
"""

from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

# Authentication (OAuth/OIDC) - Abstracted
from swap_layer.identity.platform.factory import get_identity_client

# Management (Admin Operations) - Abstracted
from swap_layer.identity.platform.management.factory import get_management_client


# ============================================================================
# OAuth Authentication (Existing - No Changes)
# ============================================================================

def login_view(request):
    """OAuth login flow - provider agnostic."""
    identity = get_identity_client(app_name='default')
    auth_url = identity.get_authorization_url(
        request=request,
        redirect_uri=request.build_absolute_uri('/auth/callback'),
        state='random_state'
    )
    return redirect(auth_url)


# ============================================================================
# User Management (NEW - Modular Architecture)
# ============================================================================

@staff_member_required
def admin_list_users(request):
    """
    List all users using the abstracted management client.
    Works with Auth0, WorkOS, or any other provider.
    """
    mgmt = get_management_client(app_name='default')
    
    # Access user management module
    users = mgmt.users.list_users(
        page=int(request.GET.get('page', 0)),
        per_page=int(request.GET.get('per_page', 50)),
        search_query=request.GET.get('q')
    )
    
    return JsonResponse({'users': users})


@staff_member_required
def admin_create_user(request):
    """Create a user - provider agnostic."""
    import json
    data = json.loads(request.body)
    
    mgmt = get_management_client(app_name='default')
    
    # User management is abstracted
    user = mgmt.users.create_user(
        email=data['email'],
        password=data.get('password'),
        email_verified=data.get('email_verified', False),
        metadata=data.get('metadata', {})
    )
    
    return JsonResponse(user, status=201)


@staff_member_required
def admin_update_user(request, user_id):
    """Update a user - provider agnostic."""
    import json
    data = json.loads(request.body)
    
    mgmt = get_management_client(app_name='default')
    
    # Update user through abstracted interface
    user = mgmt.users.update_user(
        user_id=user_id,
        email=data.get('email'),
        metadata=data.get('metadata')
    )
    
    return JsonResponse(user)


@staff_member_required
def admin_search_users(request):
    """Search users - provider agnostic."""
    mgmt = get_management_client(app_name='default')
    
    # Search using provider-specific query syntax
    # (Each provider may have different query syntax, but interface is the same)
    users = mgmt.users.search_users(
        query=request.GET.get('q', ''),
        per_page=50
    )
    
    return JsonResponse({'users': users})


# ============================================================================
# Organization Management (NEW - Modular Architecture)
# ============================================================================

@staff_member_required
def admin_list_organizations(request):
    """List organizations - provider agnostic."""
    mgmt = get_management_client(app_name='default')
    
    # Access organization management module
    orgs = mgmt.organizations.list_organizations(
        page=int(request.GET.get('page', 0)),
        per_page=int(request.GET.get('per_page', 50))
    )
    
    return JsonResponse({'organizations': orgs})


@staff_member_required
def admin_create_organization(request):
    """Create an organization - provider agnostic."""
    import json
    data = json.loads(request.body)
    
    mgmt = get_management_client(app_name='default')
    
    # Create organization through abstracted interface
    org = mgmt.organizations.create_organization(
        name=data['name'],
        display_name=data.get('display_name'),
        metadata=data.get('metadata', {})
    )
    
    return JsonResponse(org, status=201)


@staff_member_required
def admin_organization_members(request, org_id):
    """List organization members - provider agnostic."""
    mgmt = get_management_client(app_name='default')
    
    # Get members through abstracted interface
    members = mgmt.organizations.list_organization_members(
        org_id=org_id,
        page=int(request.GET.get('page', 0)),
        per_page=int(request.GET.get('per_page', 50))
    )
    
    return JsonResponse({'members': members})


@staff_member_required
def admin_add_to_organization(request, org_id):
    """Add members to organization - provider agnostic."""
    import json
    data = json.loads(request.body)
    
    mgmt = get_management_client(app_name='default')
    
    # Add members through abstracted interface
    mgmt.organizations.add_organization_members(
        org_id=org_id,
        user_ids=data['user_ids']
    )
    
    return JsonResponse({'status': 'success', 'added': len(data['user_ids'])})


# ============================================================================
# Role Management (NEW - Modular Architecture)
# ============================================================================

@staff_member_required
def admin_list_roles(request):
    """List all roles - provider agnostic."""
    mgmt = get_management_client(app_name='default')
    
    # Access role management module
    roles = mgmt.roles.list_roles(
        page=int(request.GET.get('page', 0)),
        per_page=int(request.GET.get('per_page', 50))
    )
    
    return JsonResponse({'roles': roles})


@staff_member_required
def admin_user_roles(request, user_id):
    """Manage user roles - provider agnostic."""
    mgmt = get_management_client(app_name='default')
    
    if request.method == 'GET':
        # Get user's roles
        roles = mgmt.roles.get_user_roles(user_id)
        return JsonResponse({'roles': roles})
    
    elif request.method == 'POST':
        # Assign roles to user
        import json
        data = json.loads(request.body)
        
        mgmt.roles.assign_user_roles(
            user_id=user_id,
            role_ids=data['role_ids']
        )
        return JsonResponse({'status': 'success', 'assigned': len(data['role_ids'])})
    
    elif request.method == 'DELETE':
        # Remove roles from user
        import json
        data = json.loads(request.body)
        
        mgmt.roles.remove_user_roles(
            user_id=user_id,
            role_ids=data['role_ids']
        )
        return JsonResponse({'status': 'success', 'removed': len(data['role_ids'])})


@staff_member_required
def admin_user_permissions(request, user_id):
    """Get user permissions - provider agnostic."""
    mgmt = get_management_client(app_name='default')
    
    # Get effective permissions (may be derived from roles)
    permissions = mgmt.roles.get_user_permissions(user_id)
    
    return JsonResponse({'permissions': permissions})


# ============================================================================
# Audit Logs (NEW - Modular Architecture)
# ============================================================================

@staff_member_required
def admin_audit_logs(request):
    """View audit logs - provider agnostic."""
    mgmt = get_management_client(app_name='default')
    
    # Access log management module
    logs = mgmt.logs.list_logs(
        page=int(request.GET.get('page', 0)),
        per_page=int(request.GET.get('per_page', 50)),
        query=request.GET.get('q')
    )
    
    return JsonResponse({'logs': logs})


@staff_member_required
def admin_user_logs(request, user_id):
    """Get logs for a specific user - provider agnostic."""
    mgmt = get_management_client(app_name='default')
    
    # Get user-specific logs
    logs = mgmt.logs.get_user_logs(
        user_id=user_id,
        page=int(request.GET.get('page', 0)),
        per_page=int(request.GET.get('per_page', 50))
    )
    
    return JsonResponse({'logs': logs})


# ============================================================================
# Advanced: Composing Multiple Operations
# ============================================================================

@staff_member_required
def create_user_with_org_and_role(request):
    """
    Complex operation: Create user, add to organization, assign role.
    All operations are provider-agnostic.
    """
    import json
    data = json.loads(request.body)
    
    mgmt = get_management_client(app_name='default')
    
    # 1. Create user
    user = mgmt.users.create_user(
        email=data['email'],
        password=data['password'],
        metadata={'onboarding_completed': False}
    )
    user_id = user['user_id']  # Field name may vary by provider
    
    # 2. Add to organization
    if data.get('organization_id'):
        mgmt.organizations.add_organization_members(
            org_id=data['organization_id'],
            user_ids=[user_id]
        )
    
    # 3. Assign role
    if data.get('role_ids'):
        mgmt.roles.assign_user_roles(
            user_id=user_id,
            role_ids=data['role_ids']
        )
    
    return JsonResponse({
        'user': user,
        'organization_id': data.get('organization_id'),
        'role_ids': data.get('role_ids')
    }, status=201)


# ============================================================================
# Provider-Specific Operations (When Needed)
# ============================================================================

@staff_member_required
def auth0_specific_operation(request):
    """
    Sometimes you need provider-specific features.
    You can still access the provider-specific client directly.
    """
    from swap_layer.identity.platform.providers.auth0.management import Auth0ManagementClient
    
    # Use provider-specific client
    mgmt = Auth0ManagementClient(app_name='default')
    
    # Auth0-specific operation (e.g., role permissions)
    role_id = request.GET.get('role_id')
    permissions = mgmt.roles.get_role_permissions(role_id)
    
    return JsonResponse({'permissions': permissions})


# ============================================================================
# URL Configuration
# ============================================================================

"""
# urls.py

from django.urls import path
from . import views

urlpatterns = [
    # User Management
    path('admin/users/', views.admin_list_users),
    path('admin/users/create/', views.admin_create_user),
    path('admin/users/<str:user_id>/', views.admin_update_user),
    path('admin/users/search/', views.admin_search_users),
    
    # Organization Management
    path('admin/organizations/', views.admin_list_organizations),
    path('admin/organizations/create/', views.admin_create_organization),
    path('admin/organizations/<str:org_id>/members/', views.admin_organization_members),
    path('admin/organizations/<str:org_id>/add-members/', views.admin_add_to_organization),
    
    # Role Management
    path('admin/roles/', views.admin_list_roles),
    path('admin/users/<str:user_id>/roles/', views.admin_user_roles),
    path('admin/users/<str:user_id>/permissions/', views.admin_user_permissions),
    
    # Audit Logs
    path('admin/logs/', views.admin_audit_logs),
    path('admin/users/<str:user_id>/logs/', views.admin_user_logs),
]
"""


# ============================================================================
# Configuration Example
# ============================================================================

"""
# settings.py

# OAuth Authentication
IDENTITY_PROVIDER = 'auth0'  # or 'workos'
AUTH0_DEVELOPER_DOMAIN = 'yourapp.us.auth0.com'

AUTH0_APPS = {
    'default': {
        # OAuth credentials (for user authentication)
        'client_id': os.environ['AUTH0_CLIENT_ID'],
        'client_secret': os.environ['AUTH0_CLIENT_SECRET'],
        
        # Management API credentials (for administrative operations)
        'management_client_id': os.environ['AUTH0_MGMT_CLIENT_ID'],
        'management_client_secret': os.environ['AUTH0_MGMT_CLIENT_SECRET'],
    }
}

# The same get_management_client() works for any provider
# Just change IDENTITY_PROVIDER to 'workos' and it will use WorkOS implementation
"""
