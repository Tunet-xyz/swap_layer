"""
Identity platform authentication module.
Provides OAuth/OIDC abstraction for WorkOS, Auth0, etc.
"""

from .factory import get_identity_client
from .adapter import AuthProviderAdapter
from .services import AuthenticationService
from .models import UserIdentity, AbstractUserIdentity, OAuthIdentityMixin, SSOConnectionMixin

# Convenience alias
get_provider = get_identity_client

__all__ = [
    'get_provider',
    'get_identity_client',
    'AuthProviderAdapter',
    'AuthenticationService',
    'UserIdentity',
    'AbstractUserIdentity',
    'OAuthIdentityMixin',
    'SSOConnectionMixin',
]