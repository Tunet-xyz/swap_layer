"""
WorkOS Authentication Client.

Thread-safe implementation using WorkOS SDK v5.x client pattern.
Each instance maintains its own WorkOSClient with dedicated credentials.
"""

from typing import Any

from django.conf import settings
from workos import WorkOSClient as WorkOSSDKClient
from workos.user_management import UserManagementProviderType

from ...adapter import AuthProviderAdapter


class WorkOSClient(AuthProviderAdapter):
    """
    WorkOS authentication client using SDK v5.x pattern.

    Each instance creates its own WorkOSClient with dedicated credentials,
    making it thread-safe without requiring global state manipulation.
    """

    def __init__(self, app_name: str = "default"):
        """
        Initialize WorkOS client with app-specific configuration.

        Args:
            app_name: Key in WORKOS_APPS settings dict

        Raises:
            ValueError: If app_name not found in settings
        """
        self.app_name = app_name
        self.config = settings.WORKOS_APPS.get(app_name)
        if not self.config:
            raise ValueError(
                f"WorkOS configuration for '{app_name}' not found in settings.WORKOS_APPS"
            )

        # Store credentials
        self._api_key = self.config["api_key"]
        self._client_id = self.config["client_id"]
        self._cookie_password = self.config["cookie_password"]

        # Create dedicated WorkOS client instance (SDK v5.x pattern)
        self._workos_client = WorkOSSDKClient(
            api_key=self._api_key,
            client_id=self._client_id,
        )

    @property
    def client(self):
        """Get the WorkOS SDK client instance."""
        return self._workos_client

    def get_authorization_url(self, request, redirect_uri: str, state: str | None = None) -> str:
        """
        Generate OAuth authorization URL for WorkOS AuthKit.

        Args:
            request: Django HTTP request (unused, for interface compatibility)
            redirect_uri: URL to redirect after authentication
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect the user to
        """
        return self._workos_client.user_management.get_authorization_url(
            provider=UserManagementProviderType.AuthKit, redirect_uri=redirect_uri, state=state
        )

    def exchange_code_for_user(self, request, code: str) -> dict[str, Any]:
        """
        Exchange authorization code for user data.

        Args:
            request: Django HTTP request (unused, for interface compatibility)
            code: Authorization code from OAuth callback

        Returns:
            Dict containing normalized user data and sealed session
        """
        response = self._workos_client.user_management.authenticate_with_code(
            code=code,
            session={"seal_session": True, "cookie_password": self._cookie_password},
        )

        user = response.user

        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email_verified": user.email_verified,
            "raw_user": user.to_dict(),
            "sealed_session": response.sealed_session,
        }

    def get_logout_url(self, request, return_to: str) -> str:
        """
        Generate logout URL for WorkOS session.

        Args:
            request: Django HTTP request containing session
            return_to: URL to redirect after logout

        Returns:
            Logout URL or return_to if session not found
        """
        sealed_session = request.session.get("workos_sealed_session")

        if sealed_session:
            try:
                session = self._workos_client.user_management.load_sealed_session(
                    sealed_session=sealed_session,
                    cookie_password=self._cookie_password,
                )
                return session.get_logout_url()
            except Exception:
                # If session loading fails, fallback to return_to url
                pass

        return return_to
