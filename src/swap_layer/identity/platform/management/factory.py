"""
Factory function for identity management clients.

Returns the appropriate management client based on configuration.
"""

from django.conf import settings

from .adapter import IdentityManagementClient


def get_management_client(app_name: str = "default") -> IdentityManagementClient:
    """
    Factory function to return the configured Identity Management Client.

    This allows switching vendors by changing the IDENTITY_PROVIDER Django setting.

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
    provider = getattr(settings, "IDENTITY_PROVIDER", "workos")

    if provider == "auth0":
        from ..providers.auth0.management.client import Auth0ManagementClient

        # Map 'default' to 'developer' for Auth0 legacy support if needed
        if app_name == "default":
            app_name = "developer"
        return Auth0ManagementClient(app_name=app_name)

    elif provider == "workos":
        # Get WorkOS API key from settings
        from swap_layer.settings import get_settings

        from ..providers.workos.management.client import WorkOSManagementClient

        settings_obj = get_settings()
        api_key = settings_obj.WORKOS_API_KEY
        return WorkOSManagementClient(api_key=api_key)

    else:
        raise ValueError(
            f"Unknown Identity Provider: {provider}. "
            f"Management API not implemented for this provider."
        )
