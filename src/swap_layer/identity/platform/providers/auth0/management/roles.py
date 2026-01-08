"""
Auth0 Role Management Implementation
"""

from typing import Any

from swap_layer.identity.platform.management.adapter import RoleManagementAdapter


class Auth0RoleManagement(RoleManagementAdapter):
    """
    Auth0-specific implementation of role and permission management operations.
    """

    def __init__(self, base_client):
        """
        Initialize with base client for shared functionality.

        Args:
            base_client: Auth0ManagementClient instance
        """
        self.base_client = base_client

    def list_roles(self, page: int = 0, per_page: int = 50, **kwargs) -> list[dict[str, Any]]:
        """
        List all available roles.

        Args:
            page: Page number
            per_page: Results per page
            **kwargs: Additional Auth0-specific parameters

        Returns:
            List of role objects
        """
        params = {"page": page, "per_page": per_page, **kwargs}
        return self.base_client._make_request("GET", "/roles", params=params)

    def get_role(self, role_id: str) -> dict[str, Any]:
        """
        Get role details.

        Args:
            role_id: Role ID

        Returns:
            Role object
        """
        return self.base_client._make_request("GET", f"/roles/{role_id}")

    def create_role(self, name: str, description: str | None = None, **kwargs) -> dict[str, Any]:
        """
        Create a new role.

        Args:
            name: Role name
            description: Role description
            **kwargs: Additional Auth0-specific fields

        Returns:
            Created role object
        """
        payload = {"name": name, **kwargs}

        if description:
            payload["description"] = description

        return self.base_client._make_request("POST", "/roles", json=payload)

    def update_role(
        self, role_id: str, name: str | None = None, description: str | None = None, **kwargs
    ) -> dict[str, Any]:
        """
        Update a role.

        Args:
            role_id: Role ID
            name: New name
            description: New description
            **kwargs: Additional fields to update

        Returns:
            Updated role object
        """
        payload = {}

        if name:
            payload["name"] = name

        if description:
            payload["description"] = description

        payload.update(kwargs)

        return self.base_client._make_request("PATCH", f"/roles/{role_id}", json=payload)

    def delete_role(self, role_id: str) -> None:
        """
        Delete a role.

        Args:
            role_id: Role ID
        """
        self.base_client._make_request("DELETE", f"/roles/{role_id}")

    def get_user_roles(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get roles assigned to a user.

        Args:
            user_id: Auth0 user ID

        Returns:
            List of role objects
        """
        return self.base_client._make_request("GET", f"/users/{user_id}/roles")

    def assign_user_roles(self, user_id: str, role_ids: list[str], **kwargs) -> None:
        """
        Assign roles to a user.

        Args:
            user_id: Auth0 user ID
            role_ids: List of role IDs to assign
            **kwargs: Additional Auth0-specific parameters
        """
        payload = {"roles": role_ids, **kwargs}
        self.base_client._make_request("POST", f"/users/{user_id}/roles", json=payload)

    def remove_user_roles(self, user_id: str, role_ids: list[str], **kwargs) -> None:
        """
        Remove roles from a user.

        Args:
            user_id: Auth0 user ID
            role_ids: List of role IDs to remove
            **kwargs: Additional Auth0-specific parameters
        """
        payload = {"roles": role_ids, **kwargs}
        self.base_client._make_request("DELETE", f"/users/{user_id}/roles", json=payload)

    def get_role_permissions(self, role_id: str) -> list[dict[str, Any]]:
        """
        Get permissions for a role.

        Args:
            role_id: Role ID

        Returns:
            List of permission objects
        """
        return self.base_client._make_request("GET", f"/roles/{role_id}/permissions")

    def add_role_permissions(
        self, role_id: str, permissions: list[dict[str, str]], **kwargs
    ) -> None:
        """
        Add permissions to a role.

        Args:
            role_id: Role ID
            permissions: List of permission objects with 'resource_server_identifier' and 'permission_name'
            **kwargs: Additional Auth0-specific parameters

        Example:
            >>> roles.add_role_permissions('rol_123', [
            ...     {'resource_server_identifier': 'api.example.com', 'permission_name': 'read:users'}
            ... ])
        """
        payload = {"permissions": permissions, **kwargs}
        self.base_client._make_request("POST", f"/roles/{role_id}/permissions", json=payload)

    def remove_role_permissions(
        self, role_id: str, permissions: list[dict[str, str]], **kwargs
    ) -> None:
        """
        Remove permissions from a role.

        Args:
            role_id: Role ID
            permissions: List of permission objects with 'resource_server_identifier' and 'permission_name'
            **kwargs: Additional Auth0-specific parameters
        """
        payload = {"permissions": permissions, **kwargs}
        self.base_client._make_request("DELETE", f"/roles/{role_id}/permissions", json=payload)

    def get_user_permissions(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get permissions for a user (derived from roles).

        Args:
            user_id: Auth0 user ID

        Returns:
            List of permission objects
        """
        return self.base_client._make_request("GET", f"/users/{user_id}/permissions")
