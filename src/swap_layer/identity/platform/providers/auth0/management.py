"""
Auth0 Management API v2 Client

Provides administrative operations beyond OAuth/OIDC authentication.
This is separate from the Auth0Client which handles user authentication.

Documentation: https://auth0.com/docs/api/management/v2

Usage:
    from swap_layer.identity.platform.providers.auth0.management import Auth0ManagementClient

    mgmt = Auth0ManagementClient(app_name='developer')

    # User management
    users = mgmt.list_users(page=0, per_page=50)
    user = mgmt.get_user(user_id='auth0|123')
    updated = mgmt.update_user(user_id='auth0|123', user_metadata={'tier': 'premium'})
    mgmt.delete_user(user_id='auth0|123')

    # Organization management (if using Auth0 Organizations)
    orgs = mgmt.list_organizations()
    members = mgmt.get_organization_members(org_id='org_123')
"""

from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache


class Auth0ManagementClient:
    """
    Auth0 Management API v2 client for administrative operations.

    This is separate from the Auth0Client (authentication) and provides
    full CRUD operations on users, organizations, roles, etc.

    Authentication:
        Requires a Management API access token with appropriate scopes.
        Token is obtained via Client Credentials flow and cached.
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
        self._token = None
        self._token_expires_at = 0

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

        # Request new token
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": f"https://{self.domain}/api/v2/",
        }

        response = requests.post(self.token_url, json=payload)
        response.raise_for_status()

        data = response.json()
        token = data["access_token"]
        expires_in = data.get("expires_in", 86400)  # Default 24 hours

        # Cache token (with 5 minute buffer)
        cache.set(self._token_cache_key, token, timeout=expires_in - 300)

        return token

    def _make_request(
        self, method: str, endpoint: str, params: dict | None = None, json: dict | None = None
    ) -> dict[str, Any]:
        """
        Make authenticated request to Management API.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path (e.g., '/users')
            params: Query parameters
            json: JSON request body

        Returns:
            API response as dictionary
        """
        token = self._get_management_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        url = f"{self.base_url}{endpoint}"
        response = requests.request(
            method=method, url=url, headers=headers, params=params, json=json
        )
        response.raise_for_status()

        return response.json() if response.content else {}

    # ========================================================================
    # User Management
    # ========================================================================

    def list_users(
        self,
        page: int = 0,
        per_page: int = 50,
        search_query: str | None = None,
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        List users in your Auth0 tenant.

        Args:
            page: Page number (0-indexed)
            per_page: Results per page (max 50 for public cloud)
            search_query: Lucene query syntax (e.g., 'email:"user@example.com"')
            fields: Specific fields to include in response

        Returns:
            List of user objects

        Example:
            users = mgmt.list_users(search_query='email:"*@example.com"')
        """
        params = {
            "page": page,
            "per_page": min(per_page, 50),
        }

        if search_query:
            params["q"] = search_query
            params["search_engine"] = "v3"

        if fields:
            params["fields"] = ",".join(fields)

        return self._make_request("GET", "/users", params=params)

    def get_user(self, user_id: str) -> dict[str, Any]:
        """
        Get a specific user by ID.

        Args:
            user_id: Auth0 user ID (e.g., 'auth0|123' or 'google-oauth2|456')

        Returns:
            User object
        """
        return self._make_request("GET", f"/users/{user_id}")

    def create_user(
        self,
        email: str,
        password: str | None = None,
        connection: str = "Username-Password-Authentication",
        email_verified: bool = False,
        user_metadata: dict | None = None,
        app_metadata: dict | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create a new user.

        Args:
            email: User email
            password: User password (required for database connections)
            connection: Auth0 connection name
            email_verified: Whether email is verified
            user_metadata: User-editable metadata
            app_metadata: Application metadata (not user-editable)
            **kwargs: Additional user fields (name, nickname, picture, etc.)

        Returns:
            Created user object
        """
        payload = {
            "email": email,
            "connection": connection,
            "email_verified": email_verified,
            **kwargs,
        }

        if password:
            payload["password"] = password

        if user_metadata:
            payload["user_metadata"] = user_metadata

        if app_metadata:
            payload["app_metadata"] = app_metadata

        return self._make_request("POST", "/users", json=payload)

    def update_user(
        self,
        user_id: str,
        email: str | None = None,
        user_metadata: dict | None = None,
        app_metadata: dict | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Update an existing user.

        Args:
            user_id: Auth0 user ID
            email: New email
            user_metadata: User metadata to merge
            app_metadata: App metadata to merge
            **kwargs: Additional fields to update

        Returns:
            Updated user object
        """
        payload = {}

        if email:
            payload["email"] = email

        if user_metadata:
            payload["user_metadata"] = user_metadata

        if app_metadata:
            payload["app_metadata"] = app_metadata

        payload.update(kwargs)

        return self._make_request("PATCH", f"/users/{user_id}", json=payload)

    def delete_user(self, user_id: str) -> None:
        """
        Delete a user.

        Args:
            user_id: Auth0 user ID
        """
        self._make_request("DELETE", f"/users/{user_id}")

    def search_users(self, query: str, per_page: int = 50) -> list[dict[str, Any]]:
        """
        Search users using Lucene query syntax.

        Args:
            query: Lucene search query
            per_page: Results per page

        Returns:
            List of matching users

        Example:
            users = mgmt.search_users('email:"*@example.com" AND email_verified:true')
        """
        return self.list_users(search_query=query, per_page=per_page)

    # ========================================================================
    # Organization Management (for Auth0 Organizations feature)
    # ========================================================================

    def list_organizations(self, page: int = 0, per_page: int = 50) -> list[dict[str, Any]]:
        """
        List organizations (requires Organizations feature).

        Args:
            page: Page number
            per_page: Results per page

        Returns:
            List of organization objects
        """
        params = {"page": page, "per_page": per_page}
        return self._make_request("GET", "/organizations", params=params)

    def get_organization(self, org_id: str) -> dict[str, Any]:
        """
        Get organization details.

        Args:
            org_id: Organization ID

        Returns:
            Organization object
        """
        return self._make_request("GET", f"/organizations/{org_id}")

    def get_organization_members(
        self, org_id: str, page: int = 0, per_page: int = 50
    ) -> list[dict[str, Any]]:
        """
        List members of an organization.

        Args:
            org_id: Organization ID
            page: Page number
            per_page: Results per page

        Returns:
            List of member objects
        """
        params = {"page": page, "per_page": per_page}
        return self._make_request("GET", f"/organizations/{org_id}/members", params=params)

    def add_organization_member(self, org_id: str, user_ids: list[str]) -> None:
        """
        Add members to an organization.

        Args:
            org_id: Organization ID
            user_ids: List of user IDs to add
        """
        payload = {"members": user_ids}
        self._make_request("POST", f"/organizations/{org_id}/members", json=payload)

    # ========================================================================
    # Roles and Permissions
    # ========================================================================

    def get_user_roles(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get roles assigned to a user.

        Args:
            user_id: Auth0 user ID

        Returns:
            List of role objects
        """
        return self._make_request("GET", f"/users/{user_id}/roles")

    def assign_user_roles(self, user_id: str, role_ids: list[str]) -> None:
        """
        Assign roles to a user.

        Args:
            user_id: Auth0 user ID
            role_ids: List of role IDs to assign
        """
        payload = {"roles": role_ids}
        self._make_request("POST", f"/users/{user_id}/roles", json=payload)

    def remove_user_roles(self, user_id: str, role_ids: list[str]) -> None:
        """
        Remove roles from a user.

        Args:
            user_id: Auth0 user ID
            role_ids: List of role IDs to remove
        """
        payload = {"roles": role_ids}
        self._make_request("DELETE", f"/users/{user_id}/roles", json=payload)

    # ========================================================================
    # Logs
    # ========================================================================

    def get_logs(
        self,
        page: int = 0,
        per_page: int = 50,
        query: str | None = None,
        from_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get tenant logs (audit trail).

        Args:
            page: Page number
            per_page: Results per page
            query: Lucene query to filter logs
            from_id: Checkpoint ID for checkpoint-based pagination

        Returns:
            List of log entries
        """
        params = {}

        if from_id:
            params["from"] = from_id
            params["take"] = per_page
        else:
            params["page"] = page
            params["per_page"] = per_page

        if query:
            params["q"] = query

        return self._make_request("GET", "/logs", params=params)

    # ========================================================================
    # Stats
    # ========================================================================

    def get_active_users(self) -> dict[str, Any]:
        """
        Get active users count for the tenant.

        Returns:
            Active users statistics
        """
        return self._make_request("GET", "/stats/active-users")

    def get_daily_stats(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        """
        Get daily statistics.

        Args:
            date_from: Start date (YYYYMMDD format)
            date_to: End date (YYYYMMDD format)

        Returns:
            Daily statistics
        """
        params = {"from": date_from, "to": date_to}
        return self._make_request("GET", "/stats/daily", params=params)
