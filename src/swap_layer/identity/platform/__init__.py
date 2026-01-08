"""
Identity platform authentication module.
Provides OAuth/OIDC abstraction for WorkOS, Auth0, etc.
"""

from .adapter import AuthProviderAdapter
from .factory import get_identity_client
from .models import AbstractUserIdentity, OAuthIdentityMixin, SSOConnectionMixin, UserIdentity

# Convenience alias
get_provider = get_identity_client

__all__ = [
    'get_provider',
    'get_identity_client',
    'AuthProviderAdapter',
    'UserIdentity',
    'AbstractUserIdentity',
    'OAuthIdentityMixin',
    'SSOConnectionMixin',
]
