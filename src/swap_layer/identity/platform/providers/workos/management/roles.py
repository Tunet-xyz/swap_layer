"""
WorkOS role management operations.

Handles role listing and assignment via the WorkOS Roles API.
Note: Role creation is done via the WorkOS Dashboard, not the API.
"""

from typing import Any

from swap_layer.identity.platform.management.adapter import RoleManagementAdapter

from .organizations import WorkOSAPIError


class WorkOSRoleManagement(RoleManagementAdapter):
    """WorkOS role management implementation."""

    def __init__(self, base_client):
        """Initialize with base management client.

        Args:
            base_client: WorkOSManagementClient instance
        """
        self.base_client = base_client

    def list_roles(self, organization_id: str | None = None, **kwargs) -> dict[str, Any]:
        """List roles for an organization.

        Args:
            organization_id: Filter by organization ID (required)
            **kwargs: Additional parameters

        Returns:
            Dict with role data

        Raises:
            NotImplementedError: If organization_id not provided
        """
        if organization_id:
            return self.base_client._make_request("GET", f"/organizations/{organization_id}/roles")
        raise NotImplementedError("WorkOS requires organization_id to list roles")

    def get_role(self, role_id: str) -> dict[str, Any]:
        """Get role by ID.

        Note: WorkOS uses role slugs, not IDs, and doesn't support individual role retrieval.

        Args:
            role_id: Role slug

        Raises:
            NotImplementedError: WorkOS doesn't support this operation
        """
        raise NotImplementedError("WorkOS does not support getting individual roles by ID")

    def create_role(
        self,
        name: str,
        description: str | None = None,
        permissions: list[str] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Create a new role.

        Note: WorkOS roles are created via the Dashboard, not the API.

        Args:
            name: Role name
            description: Role description
            permissions: List of permissions
            **kwargs: Additional properties

        Raises:
            NotImplementedError: WorkOS doesn't support this operation
        """
        raise NotImplementedError("WorkOS does not support creating roles via API")

    def delete_role(self, role_id: str) -> bool:
        """Delete a role.

        Note: WorkOS roles are managed via the Dashboard, not the API.

        Args:
            role_id: Role ID

        Raises:
            NotImplementedError: WorkOS doesn't support this operation
        """
        raise NotImplementedError("WorkOS does not support deleting roles via API")

    def assign_role_to_user(
        self, user_id: str, role_id: str, organization_id: str | None = None
    ) -> dict[str, Any]:
        """Assign a role to a user via organization membership.

        Args:
            user_id: User ID
            role_id: Role slug
            organization_id: Organization ID (required)

        Returns:
            Updated membership object

        Raises:
            ValueError: If organization_id not provided
            WorkOSAPIError: If membership not found
        """
        if not organization_id:
            raise ValueError("organization_id is required for WorkOS role assignment")

        memberships_resp = self.base_client._make_request(
            "GET",
            "/user_management/organization_memberships",
            params={"user_id": user_id, "organization_id": organization_id},
        )
        memberships = memberships_resp.get("data", [])
        if not memberships:
            raise WorkOSAPIError(404, "Membership not found", {})

        membership_id = memberships[0].get("id")
        return self.base_client._make_request(
            "PUT",
            f"/user_management/organization_memberships/{membership_id}",
            json={"role_slug": role_id},
        )

    def remove_role_from_user(
        self, user_id: str, role_id: str, organization_id: str | None = None
    ) -> bool:
        """Remove a role from a user.

        Note: WorkOS doesn't support removing roles, only updating to a different role.

        Args:
            user_id: User ID
            role_id: Role ID
            organization_id: Organization ID

        Raises:
            NotImplementedError: WorkOS doesn't support this operation
        """
        raise NotImplementedError(
            "WorkOS does not support removing roles; update to a different role instead"
        )

    def get_user_roles(
        self, user_id: str, organization_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get roles assigned to a user.

        Args:
            user_id: User ID
            organization_id: Organization ID to filter by

        Returns:
            List of role objects
        """
        params = {"user_id": user_id}
        if organization_id:
            params["organization_id"] = organization_id

        memberships_resp = self.base_client._make_request(
            "GET", "/user_management/organization_memberships", params=params
        )
        roles = [m["role"] for m in memberships_resp.get("data", []) if m.get("role")]
        return roles
