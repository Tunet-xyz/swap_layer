"""
Example: Using Auth0 Authentication + Management API Together

This example demonstrates how to use both OAuth authentication and
Management API for a complete user management system.
"""

from django.shortcuts import redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from swap_layer.identity.platform.factory import get_identity_client
from swap_layer.identity.platform.providers.auth0.management import Auth0ManagementClient
import secrets


# ============================================================================
# OAuth Authentication Flow (Your Current Implementation)
# ============================================================================

def login_view(request):
    """
    Initiate OAuth login flow.
    Uses your abstracted AuthProviderAdapter.
    """
    identity = get_identity_client(app_name='developer')
    
    # Generate CSRF state
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state
    
    # Get authorization URL (abstracted across providers)
    auth_url = identity.get_authorization_url(
        request=request,
        redirect_uri=request.build_absolute_uri('/auth/callback'),
        state=state
    )
    
    return redirect(auth_url)


def callback_view(request):
    """
    Handle OAuth callback.
    Uses your abstracted AuthProviderAdapter.
    """
    # Verify state
    if request.GET.get('state') != request.session.get('oauth_state'):
        return HttpResponse('Invalid state', status=400)
    
    code = request.GET.get('code')
    if not code:
        return HttpResponse('No code provided', status=400)
    
    # Exchange code for user data (abstracted)
    identity = get_identity_client(app_name='developer')
    user_data = identity.exchange_code_for_user(request, code)
    
    # Get or create Django user
    from django.contrib.auth.models import User
    user, created = User.objects.get_or_create(
        username=user_data['email'],
        defaults={
            'email': user_data['email'],
            'first_name': user_data.get('first_name', ''),
            'last_name': user_data.get('last_name', ''),
        }
    )
    
    # Log user in
    login(request, user)
    
    return redirect('dashboard')


def logout_view(request):
    """
    Handle logout with provider.
    Uses your abstracted AuthProviderAdapter.
    """
    identity = get_identity_client(app_name='developer')
    
    # Logout from Django
    logout(request)
    
    # Get provider logout URL (abstracted)
    logout_url = identity.get_logout_url(
        request=request,
        return_to=request.build_absolute_uri('/')
    )
    
    return redirect(logout_url)


# ============================================================================
# User Management Operations (Management API - Provider Specific)
# ============================================================================

@staff_member_required
def admin_list_users(request):
    """
    Admin endpoint to list all users in Auth0.
    Uses Management API (provider-specific).
    """
    mgmt = Auth0ManagementClient(app_name='developer')
    
    # Get pagination parameters
    page = int(request.GET.get('page', 0))
    per_page = int(request.GET.get('per_page', 50))
    search_query = request.GET.get('q')
    
    # List users via Management API
    users = mgmt.list_users(
        page=page,
        per_page=per_page,
        search_query=search_query
    )
    
    return JsonResponse({
        'users': users,
        'page': page,
        'per_page': per_page
    })


@staff_member_required
def admin_create_user(request):
    """
    Admin endpoint to create a user in Auth0.
    Uses Management API (provider-specific).
    """
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)
    
    import json
    data = json.loads(request.body)
    
    mgmt = Auth0ManagementClient(app_name='developer')
    
    # Create user via Management API
    user = mgmt.create_user(
        email=data['email'],
        password=data.get('password'),
        email_verified=data.get('email_verified', False),
        user_metadata=data.get('user_metadata', {}),
        connection='Username-Password-Authentication'
    )
    
    return JsonResponse(user, status=201)


@staff_member_required
def admin_update_user(request, user_id):
    """
    Admin endpoint to update a user in Auth0.
    Uses Management API (provider-specific).
    """
    if request.method != 'PATCH':
        return HttpResponse('Method not allowed', status=405)
    
    import json
    data = json.loads(request.body)
    
    mgmt = Auth0ManagementClient(app_name='developer')
    
    # Update user via Management API
    user = mgmt.update_user(
        user_id=user_id,
        email=data.get('email'),
        user_metadata=data.get('user_metadata'),
        app_metadata=data.get('app_metadata')
    )
    
    return JsonResponse(user)


@staff_member_required
def admin_delete_user(request, user_id):
    """
    Admin endpoint to delete a user from Auth0.
    Uses Management API (provider-specific).
    """
    if request.method != 'DELETE':
        return HttpResponse('Method not allowed', status=405)
    
    mgmt = Auth0ManagementClient(app_name='developer')
    
    # Delete user via Management API
    mgmt.delete_user(user_id)
    
    return HttpResponse(status=204)


@staff_member_required
def admin_search_users(request):
    """
    Admin endpoint to search users.
    Uses Management API (provider-specific).
    """
    query = request.GET.get('q', '')
    
    mgmt = Auth0ManagementClient(app_name='developer')
    
    # Search users using Lucene syntax
    users = mgmt.search_users(query)
    
    return JsonResponse({'users': users})


# ============================================================================
# Advanced: User Provisioning (Combining Both)
# ============================================================================

@login_required
def upgrade_to_premium(request):
    """
    Example: Upgrade user to premium tier.
    Uses Management API to update Auth0 user metadata.
    """
    # Get current user's Auth0 ID from your database
    # (You'd store this during OAuth callback)
    auth0_user_id = request.user.profile.auth0_user_id  # Example
    
    mgmt = Auth0ManagementClient(app_name='developer')
    
    # Update user metadata in Auth0
    mgmt.update_user(
        user_id=auth0_user_id,
        user_metadata={
            'tier': 'premium',
            'upgraded_at': '2026-01-06T00:00:00Z'
        }
    )
    
    # Update local database
    request.user.profile.tier = 'premium'
    request.user.profile.save()
    
    return JsonResponse({'status': 'success', 'tier': 'premium'})


# ============================================================================
# Advanced: Organization Management
# ============================================================================

@staff_member_required
def admin_list_organizations(request):
    """
    Admin endpoint to list Auth0 Organizations.
    Uses Management API (provider-specific).
    """
    mgmt = Auth0ManagementClient(app_name='developer')
    
    # List organizations
    orgs = mgmt.list_organizations()
    
    return JsonResponse({'organizations': orgs})


@staff_member_required
def admin_organization_members(request, org_id):
    """
    Admin endpoint to list members of an organization.
    Uses Management API (provider-specific).
    """
    mgmt = Auth0ManagementClient(app_name='developer')
    
    # Get organization members
    members = mgmt.get_organization_members(org_id)
    
    return JsonResponse({'members': members})


@staff_member_required
def admin_add_to_organization(request, org_id):
    """
    Admin endpoint to add users to an organization.
    Uses Management API (provider-specific).
    """
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)
    
    import json
    data = json.loads(request.body)
    user_ids = data['user_ids']  # List of Auth0 user IDs
    
    mgmt = Auth0ManagementClient(app_name='developer')
    
    # Add members to organization
    mgmt.add_organization_member(org_id, user_ids)
    
    return JsonResponse({'status': 'success', 'added': len(user_ids)})


# ============================================================================
# Advanced: Audit Logs
# ============================================================================

@staff_member_required
def admin_audit_logs(request):
    """
    Admin endpoint to view authentication audit logs.
    Uses Management API (provider-specific).
    """
    mgmt = Auth0ManagementClient(app_name='developer')
    
    page = int(request.GET.get('page', 0))
    per_page = int(request.GET.get('per_page', 50))
    query = request.GET.get('q')  # Lucene query syntax
    
    # Get logs
    logs = mgmt.get_logs(page=page, per_page=per_page, query=query)
    
    return JsonResponse({
        'logs': logs,
        'page': page,
        'per_page': per_page
    })


# ============================================================================
# Advanced: Role Management
# ============================================================================

@staff_member_required
def admin_user_roles(request, user_id):
    """
    Admin endpoint to manage user roles.
    Uses Management API (provider-specific).
    """
    mgmt = Auth0ManagementClient(app_name='developer')
    
    if request.method == 'GET':
        # Get user's roles
        roles = mgmt.get_user_roles(user_id)
        return JsonResponse({'roles': roles})
    
    elif request.method == 'POST':
        # Assign roles to user
        import json
        data = json.loads(request.body)
        role_ids = data['role_ids']
        
        mgmt.assign_user_roles(user_id, role_ids)
        return JsonResponse({'status': 'success', 'assigned': len(role_ids)})
    
    elif request.method == 'DELETE':
        # Remove roles from user
        import json
        data = json.loads(request.body)
        role_ids = data['role_ids']
        
        mgmt.remove_user_roles(user_id, role_ids)
        return JsonResponse({'status': 'success', 'removed': len(role_ids)})
    
    return HttpResponse('Method not allowed', status=405)


# ============================================================================
# URL Configuration Example
# ============================================================================

"""
# urls.py

from django.urls import path
from . import views

urlpatterns = [
    # OAuth Authentication (abstracted)
    path('auth/login/', views.login_view, name='login'),
    path('auth/callback/', views.callback_view, name='callback'),
    path('auth/logout/', views.logout_view, name='logout'),
    
    # User Management (Management API)
    path('admin/users/', views.admin_list_users, name='admin_users'),
    path('admin/users/create/', views.admin_create_user, name='admin_create_user'),
    path('admin/users/<str:user_id>/', views.admin_update_user, name='admin_update_user'),
    path('admin/users/<str:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    path('admin/users/search/', views.admin_search_users, name='admin_search_users'),
    
    # Organization Management
    path('admin/organizations/', views.admin_list_organizations, name='admin_organizations'),
    path('admin/organizations/<str:org_id>/members/', views.admin_organization_members, name='admin_org_members'),
    path('admin/organizations/<str:org_id>/add-members/', views.admin_add_to_organization, name='admin_add_to_org'),
    
    # Audit & Roles
    path('admin/logs/', views.admin_audit_logs, name='admin_logs'),
    path('admin/users/<str:user_id>/roles/', views.admin_user_roles, name='admin_user_roles'),
]
"""


# ============================================================================
# Settings Configuration Example
# ============================================================================

"""
# settings.py

# OAuth Authentication (existing)
IDENTITY_PROVIDER = 'auth0'
AUTH0_DEVELOPER_DOMAIN = 'yourapp.us.auth0.com'

AUTH0_APPS = {
    'developer': {
        # OAuth credentials (for user authentication)
        'client_id': os.environ['AUTH0_CLIENT_ID'],
        'client_secret': os.environ['AUTH0_CLIENT_SECRET'],
        
        # Management API credentials (for administrative operations)
        # Create a "Machine to Machine" application in Auth0 Dashboard
        'management_client_id': os.environ.get('AUTH0_MGMT_CLIENT_ID'),
        'management_client_secret': os.environ.get('AUTH0_MGMT_CLIENT_SECRET'),
    }
}

# SwapLayer Configuration (optional, if using SwapLayerSettings)
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    identity={
        'provider': 'auth0',
        'auth0_apps': AUTH0_APPS,
        'auth0_domain': AUTH0_DEVELOPER_DOMAIN,
    }
)
"""
