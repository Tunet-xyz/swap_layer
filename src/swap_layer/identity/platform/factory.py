from django.conf import settings

from .adapter import AuthProviderAdapter


def get_identity_client(app_name="default") -> AuthProviderAdapter:
    """
    Factory function to return the configured Identity Provider Client.
    This allows switching vendors by changing the IDENTITY_PROVIDER Django setting.
    """
    provider = getattr(settings, "IDENTITY_PROVIDER", "workos")

    if provider == "workos":
        from .providers.workos.client import WorkOSClient

        return WorkOSClient(app_name=app_name)
    elif provider == "auth0":
        from .providers.auth0.client import Auth0Client

        # Map 'default' to 'developer' for Auth0 legacy support if needed
        if app_name == "default":
            app_name = "developer"
        return Auth0Client(app_name=app_name)
    else:
        raise ValueError(f"Unknown Identity Provider: {provider}")
