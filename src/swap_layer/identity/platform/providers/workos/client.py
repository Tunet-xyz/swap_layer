"""
WorkOS Authentication Client.

Thread-safe implementation that properly manages WorkOS configuration
to avoid global state issues in multi-tenant environments.
"""

import threading
from typing import Any

import workos
from django.conf import settings
from workos.user_management import UserManagementProviderType

from ...adapter import AuthProviderAdapter

# Thread lock for safe WorkOS configuration
_workos_lock = threading.Lock()


class WorkOSClient(AuthProviderAdapter):
    """
    Thread-safe WorkOS authentication client.

    Uses thread locking to safely configure WorkOS SDK for multi-tenant
    usage where different apps may have different credentials.
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

    def _configure_workos(self):
        """Thread-safe configuration of WorkOS SDK."""
        with _workos_lock:
            workos.api_key = self._api_key
            workos.client_id = self._client_id

    @property
    def client(self):
        """Get the WorkOS SDK client instance (thread-safe)."""
        self._configure_workos()
        return workos.client

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
        self._configure_workos()
        return workos.client.user_management.get_authorization_url(
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
        self._configure_workos()
        response = workos.client.user_management.authenticate_with_code(
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
                self._configure_workos()
                session = workos.client.user_management.load_sealed_session(
                    sealed_session=sealed_session,
                    cookie_password=self._cookie_password,
                )
                return session.get_logout_url()
            except Exception:
                # If session loading fails, fallback to return_to url
                pass

        return return_to
