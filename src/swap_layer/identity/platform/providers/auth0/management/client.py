"""
Auth0 Management API Client

Provides administrative operations for Auth0 using the Management API v2
with resilient HTTP handling and automatic retries.

Documentation: https://auth0.com/docs/api/management/v2
"""

import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache

from swap_layer.http import ResilientSession, resilient_request
from swap_layer.identity.platform.management.adapter import IdentityManagementClient

from .logs import Auth0LogManagement
from .organizations import Auth0OrganizationManagement
from .roles import Auth0RoleManagement
from .users import Auth0UserManagement

logger = logging.getLogger(__name__)


class Auth0ManagementClient(IdentityManagementClient):
    """
    Auth0 Management API v2 client for administrative operations.

    Composes individual management adapters for users, organizations, roles, and logs.

    Usage:
        >>> mgmt = Auth0ManagementClient(app_name='developer')
        >>>
        >>> # User management
        >>> users = mgmt.users.list_users()
        >>> user = mgmt.users.create_user(email='new@example.com', password='secure123')
        >>>
        >>> # Organization management
        >>> orgs = mgmt.organizations.list_organizations()
        >>> mgmt.organizations.add_organization_members(org_id='org_123', user_ids=['auth0|123'])
        >>>
        >>> # Role management
        >>> mgmt.roles.assign_user_roles(user_id='auth0|123', role_ids=['rol_abc'])
        >>>
        >>> # Audit logs
        >>> logs = mgmt.logs.list_logs(query='type:f')
    """

    def __init__(self, app_name: str = "developer"):
        """
        Initialize Management API client.

        Args:
            app_name: Auth0 app configuration name from settings
        """
        self.app_name = app_name
        self.config = settings.AUTH0_APPS.get(app_name)
        if not self.config:
            raise ValueError(
                f"Auth0 configuration for '{app_name}' not found in settings.AUTH0_APPS"
            )

        self.domain = settings.AUTH0_DEVELOPER_DOMAIN
        self.base_url = f"https://{self.domain}/api/v2"
        self.token_url = f"https://{self.domain}/oauth/token"

        # Management API credentials (different from OAuth client credentials)
        # These should be configured as a "Machine to Machine" application
        # with Management API permissions
        self.client_id = self.config.get("management_client_id") or self.config["client_id"]
        self.client_secret = (
            self.config.get("management_client_secret") or self.config["client_secret"]
        )

        # Token caching
        self._token_cache_key = f"auth0_mgmt_token_{app_name}"

        # Create resilient session for API requests
        self._session = None  # Lazily initialized after token fetch

        # Initialize module adapters
        self._users = Auth0UserManagement(self)
        self._organizations = Auth0OrganizationManagement(self)
        self._roles = Auth0RoleManagement(self)
        self._logs = Auth0LogManagement(self)

    # ========================================================================
    # Public Properties (IdentityManagementClient interface)
    # ========================================================================

    @property
    def users(self) -> Auth0UserManagement:
        """Access to user management operations."""
        return self._users

    @property
    def organizations(self) -> Auth0OrganizationManagement:
        """Access to organization management operations."""
        return self._organizations

    @property
    def roles(self) -> Auth0RoleManagement:
        """Access to role management operations."""
        return self._roles

    @property
    def logs(self) -> Auth0LogManagement:
        """Access to log management operations."""
        return self._logs

    # ========================================================================
    # Internal Methods (shared across modules)
    # ========================================================================

    def _get_management_token(self) -> str:
        """
        Obtain Management API access token via Client Credentials flow.
        Token is cached to avoid unnecessary requests.

        Returns:
            Management API access token
        """
        # Check cache first
        cached_token = cache.get(self._token_cache_key)
        if cached_token:
            return cached_token

        # Request new token with retry support
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": f"https://{self.domain}/api/v2/",
        }

        try:
            response = resilient_request(
                "POST",
                self.token_url,
                json=payload,
                timeout=30,
                max_retries=3,
            )
            data = response.json()
        except Exception as e:
            logger.error(f"Failed to obtain Auth0 management token: {e}")
            raise

        token = data["access_token"]
        expires_in = data.get("expires_in", 86400)  # Default 24 hours

        # Cache token (with 5 minute buffer)
        cache.set(self._token_cache_key, token, timeout=expires_in - 300)

        return token

    def _get_session(self) -> ResilientSession:
        """Get or create the resilient session with current auth token."""
        token = self._get_management_token()

        # Recreate session if token changed or not initialized
        if self._session is None:
            self._session = ResilientSession(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                timeout=30,
                max_retries=3,
            )
        else:
            # Update auth header in case token refreshed
            self._session.session.headers["Authorization"] = f"Bearer {token}"

        return self._session

    def _make_request(
        self, method: str, endpoint: str, params: dict | None = None, json: dict | None = None
    ) -> dict[str, Any]:
        """
        Make authenticated request to Management API with automatic retries.

        This is the core method used by all management modules.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path (e.g., '/users')
            params: Query parameters
            json: JSON request body

        Returns:
            API response as dictionary

        Raises:
            requests.HTTPError: If request fails after retries
        """
        session = self._get_session()

        try:
            response = session._make_request(
                method=method,
                endpoint=endpoint,
                params=params,
                json=json,
            )
            return response.json() if response.content else {}
        except Exception as e:
            logger.error(f"Auth0 API request failed: {method} {endpoint} - {e}")
            raise

    # ========================================================================
    # Additional Helper Methods
    # ========================================================================

    def get_stats(self) -> dict[str, Any]:
        """
        Get tenant statistics.

        Returns:
            Statistics about active users, logins, etc.
        """
        return self._make_request("GET", "/stats/active-users")

    def get_daily_stats(self, date_from: str, date_to: str) -> list:
        """
        Get daily statistics for a date range.

        Args:
            date_from: Start date (YYYYMMDD format)
            date_to: End date (YYYYMMDD format)

        Returns:
            Daily statistics
        """
        params = {"from": date_from, "to": date_to}
        return self._make_request("GET", "/stats/daily", params=params)
