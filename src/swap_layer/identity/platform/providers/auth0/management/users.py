"""
Auth0 User Management Implementation
"""

from typing import Any

from swap_layer.identity.platform.management.adapter import UserManagementAdapter


class Auth0UserManagement(UserManagementAdapter):
    """
    Auth0-specific implementation of user management operations.
    """

    def __init__(self, base_client):
        """
        Initialize with base client for shared functionality.

        Args:
            base_client: Auth0ManagementClient instance
        """
        self.base_client = base_client

    def list_users(
        self,
        page: int = 0,
        per_page: int = 50,
        search_query: str | None = None,
        fields: list[str] | None = None,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        List users in Auth0 tenant.

        Args:
            page: Page number (0-indexed)
            per_page: Results per page (max 50)
            search_query: Lucene query syntax (e.g., 'email:"user@example.com"')
            fields: Specific fields to include
            **kwargs: Additional Auth0-specific parameters

        Returns:
            List of user objects
        """
        params = {"page": page, "per_page": min(per_page, 50), **kwargs}

        if search_query:
            params["q"] = search_query
            params["search_engine"] = "v3"

        if fields:
            params["fields"] = ",".join(fields)

        return self.base_client._make_request("GET", "/users", params=params)

    def get_user(self, user_id: str) -> dict[str, Any]:
        """
        Get a specific user by ID.

        Args:
            user_id: Auth0 user ID (e.g., 'auth0|123')

        Returns:
            User object
        """
        return self.base_client._make_request("GET", f"/users/{user_id}")

    def create_user(
        self,
        email: str,
        password: str | None = None,
        email_verified: bool = False,
        metadata: dict | None = None,
        connection: str = "Username-Password-Authentication",
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create a new user in Auth0.

        Args:
            email: User email
            password: User password (required for database connections)
            email_verified: Whether email is verified
            metadata: User metadata (will be stored as user_metadata)
            connection: Auth0 connection name
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

        if metadata:
            payload["user_metadata"] = metadata

        return self.base_client._make_request("POST", "/users", json=payload)

    def update_user(
        self, user_id: str, email: str | None = None, metadata: dict | None = None, **kwargs
    ) -> dict[str, Any]:
        """
        Update an existing user.

        Args:
            user_id: Auth0 user ID
            email: New email
            metadata: User metadata to merge
            **kwargs: Additional fields to update

        Returns:
            Updated user object
        """
        payload = {}

        if email:
            payload["email"] = email

        if metadata:
            payload["user_metadata"] = metadata

        payload.update(kwargs)

        return self.base_client._make_request("PATCH", f"/users/{user_id}", json=payload)

    def delete_user(self, user_id: str) -> None:
        """
        Delete a user from Auth0.

        Args:
            user_id: Auth0 user ID
        """
        self.base_client._make_request("DELETE", f"/users/{user_id}")

    def search_users(self, query: str, per_page: int = 50, **kwargs) -> list[dict[str, Any]]:
        """
        Search users using Lucene query syntax.

        Args:
            query: Lucene search query
            per_page: Results per page
            **kwargs: Additional Auth0-specific parameters

        Returns:
            List of matching users

        Example:
            >>> users.search_users('email:"*@example.com" AND email_verified:true')
        """
        return self.list_users(search_query=query, per_page=per_page, **kwargs)
