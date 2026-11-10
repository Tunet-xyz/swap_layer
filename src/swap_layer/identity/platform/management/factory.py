"""
Factory function for identity management clients.

Returns the appropriate management client based on configuration.
"""

from .._config import identity_provider, workos_app_config
from .adapter import IdentityManagementClient


def get_management_client(app_name: str = "default") -> IdentityManagementClient:
    """
    Factory function to return the configured Identity Management Client.

    The provider comes from SWAPLAYER.identity.provider (or the legacy
    IDENTITY_PROVIDER Django setting when SwapLayer settings have no identity).

    Args:
        app_name: Application name from provider configuration

    Returns:
        IdentityManagementClient instance for the configured provider

    Raises:
        ValueError: If provider is unknown or not configured

    Example:
        >>> mgmt = get_management_client()
        >>> users = mgmt.users.list_users()
        >>> mgmt.users.create_user(email='new@example.com')
    """
    provider = identity_provider()

    if provider == "auth0":
        from ..providers.auth0.management.client import Auth0ManagementClient

        # Map 'default' to 'developer' for Auth0 legacy support if needed
        if app_name == "default":
            app_name = "developer"
        return Auth0ManagementClient(app_name=app_name)

    elif provider == "workos":
        from ..providers.workos.management.client import WorkOSManagementClient

        return WorkOSManagementClient(api_key=workos_app_config(app_name).api_key)

    else:
        raise ValueError(
            f"Unknown Identity Provider: {provider}. "
            f"Management API not implemented for this provider."
        )
