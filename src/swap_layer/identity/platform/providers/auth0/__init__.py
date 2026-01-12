"""
Auth0 Identity Provider

Provides both OAuth/OIDC authentication (client.py) and
Management API v2 administrative operations (management/).

Usage:
    # For OAuth authentication (abstracted)
    from swap_layer.identity.platform.factory import get_identity_client
    auth = get_identity_client(app_name='default')
    auth_url = auth.get_authorization_url(request, redirect_uri='...')

    # For administrative operations (abstracted)
    from swap_layer.identity.platform.management.factory import get_management_client
    mgmt = get_management_client(app_name='default')
    users = mgmt.users.list_users()
    mgmt.organizations.add_organization_members(org_id='org_123', user_ids=['user_123'])
    mgmt.roles.assign_user_roles(user_id='user_123', role_ids=['rol_abc'])

    # Or use provider-specific client directly
    from swap_layer.identity.platform.providers.auth0.management import Auth0ManagementClient
    mgmt = Auth0ManagementClient(app_name='default')
"""

from .client import Auth0Client
from .management import Auth0ManagementClient

__all__ = ["Auth0Client", "Auth0ManagementClient"]
