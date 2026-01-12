"""
Identity platform authentication module.
Provides OAuth/OIDC abstraction for WorkOS, Auth0, etc.

Note: Django models (UserIdentity, OAuthIdentityMixin, etc.) must be imported
directly when needed to avoid Django configuration requirements:
    from swap_layer.identity.platform.models import UserIdentity
"""

from .adapter import AuthProviderAdapter
from .factory import get_identity_client

# DO NOT import models at module level - they require Django to be configured
# from .models import AbstractUserIdentity, OAuthIdentityMixin, SSOConnectionMixin, UserIdentity

# Convenience alias
get_provider = get_identity_client

__all__ = [
    "get_provider",
    "get_identity_client",
    "AuthProviderAdapter",
    # Models available via: from swap_layer.identity.platform.models import ...
    # 'UserIdentity',
    # 'AbstractUserIdentity',
    # 'OAuthIdentityMixin',
    # 'SSOConnectionMixin',
]
