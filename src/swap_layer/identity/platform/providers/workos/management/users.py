"""
WorkOS user management operations.

Handles user CRUD operations via the WorkOS AuthKit user management API.
"""

from typing import Any

from swap_layer.identity.platform.management.adapter import UserManagementAdapter


class WorkOSUserManagement(UserManagementAdapter):
    """WorkOS user management implementation."""

    def __init__(self, base_client):
        """Initialize with base management client.

        Args:
            base_client: WorkOSManagementClient instance
        """
        self.base_client = base_client

    def list_users(
        self,
        email: str | None = None,
        organization_id: str | None = None,
        limit: int = 50,
        **kwargs,
    ) -> dict[str, Any]:
        """List users with optional filters.

        Args:
            email: Filter by email address
            organization_id: Filter by organization ID
            limit: Number of results to return
            **kwargs: Additional query parameters (before, after, order)

        Returns:
            Dict with 'data' (list of users) and 'listMetadata'
        """
        params = {"limit": limit}
        if email:
            params["email"] = email
        if organization_id:
            params["organization_id"] = organization_id
        params.update(kwargs)
        return self.base_client._make_request("GET", "/user_management/users", params=params)

    def get_user(self, user_id: str) -> dict[str, Any]:
        """Get user by ID.

        Args:
            user_id: WorkOS user ID

        Returns:
            User object
        """
        return self.base_client._make_request("GET", f"/user_management/users/{user_id}")

    def create_user(
        self,
        email: str,
        password: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        email_verified: bool = False,
        **kwargs,
    ) -> dict[str, Any]:
        """Create a new user.

        Args:
            email: User email address
            password: User password
            first_name: User first name
            last_name: User last name
            email_verified: Whether email is verified
            **kwargs: Additional user properties (external_id, metadata)

        Returns:
            Created user object
        """
        data = {"email": email, "email_verified": email_verified}
        if password:
            data["password"] = password
        if first_name:
            data["first_name"] = first_name
        if last_name:
            data["last_name"] = last_name
        data.update(kwargs)
        return self.base_client._make_request("POST", "/user_management/users", json=data)

    def update_user(
        self,
        user_id: str,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        email_verified: bool | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Update an existing user.

        Args:
            user_id: WorkOS user ID
            first_name: Updated first name
            last_name: Updated last name
            email: Updated email
            email_verified: Updated email verification status
            **kwargs: Additional properties to update (password, external_id, metadata)

        Returns:
            Updated user object
        """
        data = {}
        if first_name is not None:
            data["first_name"] = first_name
        if last_name is not None:
            data["last_name"] = last_name
        if email is not None:
            data["email"] = email
        if email_verified is not None:
            data["email_verified"] = email_verified
        data.update(kwargs)
        return self.base_client._make_request("PUT", f"/user_management/users/{user_id}", json=data)

    def delete_user(self, user_id: str) -> bool:
        """Delete a user.

        Args:
            user_id: WorkOS user ID

        Returns:
            True if successful
        """
        self.base_client._make_request("DELETE", f"/user_management/users/{user_id}")
        return True

    def search_users(self, query: str, **kwargs) -> dict[str, Any]:
        """Search users by email.

        Args:
            query: Email to search for
            **kwargs: Additional search parameters

        Returns:
            Dict with search results
        """
        return self.list_users(email=query, **kwargs)
