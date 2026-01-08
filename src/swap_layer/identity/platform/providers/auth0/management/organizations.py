"""
Auth0 Organization Management Implementation
"""

from typing import Any

from swap_layer.identity.platform.management.adapter import OrganizationManagementAdapter


class Auth0OrganizationManagement(OrganizationManagementAdapter):
    """
    Auth0-specific implementation of organization management operations.

    Note: Requires Auth0 Organizations feature to be enabled on your tenant.
    """

    def __init__(self, base_client):
        """
        Initialize with base client for shared functionality.

        Args:
            base_client: Auth0ManagementClient instance
        """
        self.base_client = base_client

    def list_organizations(
        self, page: int = 0, per_page: int = 50, **kwargs
    ) -> list[dict[str, Any]]:
        """
        List organizations in Auth0 tenant.

        Args:
            page: Page number (0-indexed)
            per_page: Results per page
            **kwargs: Additional Auth0-specific parameters

        Returns:
            List of organization objects
        """
        params = {"page": page, "per_page": per_page, **kwargs}
        return self.base_client._make_request("GET", "/organizations", params=params)

    def get_organization(self, org_id: str) -> dict[str, Any]:
        """
        Get organization details.

        Args:
            org_id: Organization ID

        Returns:
            Organization object
        """
        return self.base_client._make_request("GET", f"/organizations/{org_id}")

    def create_organization(
        self,
        name: str,
        display_name: str | None = None,
        metadata: dict | None = None,
        branding: dict | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create a new organization.

        Args:
            name: Organization name/slug (unique)
            display_name: Human-readable display name
            metadata: Organization metadata
            branding: Branding configuration (logo, colors)
            **kwargs: Additional Auth0-specific fields

        Returns:
            Created organization object
        """
        payload = {"name": name, **kwargs}

        if display_name:
            payload["display_name"] = display_name

        if metadata:
            payload["metadata"] = metadata

        if branding:
            payload["branding"] = branding

        return self.base_client._make_request("POST", "/organizations", json=payload)

    def update_organization(
        self,
        org_id: str,
        name: str | None = None,
        display_name: str | None = None,
        metadata: dict | None = None,
        branding: dict | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Update an organization.

        Args:
            org_id: Organization ID
            name: New name/slug
            display_name: New display name
            metadata: Metadata to merge
            branding: Branding configuration
            **kwargs: Additional fields to update

        Returns:
            Updated organization object
        """
        payload = {}

        if name:
            payload["name"] = name

        if display_name:
            payload["display_name"] = display_name

        if metadata:
            payload["metadata"] = metadata

        if branding:
            payload["branding"] = branding

        payload.update(kwargs)

        return self.base_client._make_request("PATCH", f"/organizations/{org_id}", json=payload)

    def delete_organization(self, org_id: str) -> None:
        """
        Delete an organization.

        Args:
            org_id: Organization ID
        """
        self.base_client._make_request("DELETE", f"/organizations/{org_id}")

    def list_organization_members(
        self, org_id: str, page: int = 0, per_page: int = 50, **kwargs
    ) -> list[dict[str, Any]]:
        """
        List members of an organization.

        Args:
            org_id: Organization ID
            page: Page number
            per_page: Results per page
            **kwargs: Additional Auth0-specific parameters

        Returns:
            List of member objects
        """
        params = {"page": page, "per_page": per_page, **kwargs}
        return self.base_client._make_request(
            "GET", f"/organizations/{org_id}/members", params=params
        )

    def add_organization_members(self, org_id: str, user_ids: list[str], **kwargs) -> None:
        """
        Add members to an organization.

        Args:
            org_id: Organization ID
            user_ids: List of user IDs to add
            **kwargs: Additional Auth0-specific parameters
        """
        payload = {"members": user_ids, **kwargs}
        self.base_client._make_request("POST", f"/organizations/{org_id}/members", json=payload)

    def remove_organization_members(self, org_id: str, user_ids: list[str], **kwargs) -> None:
        """
        Remove members from an organization.

        Args:
            org_id: Organization ID
            user_ids: List of user IDs to remove
            **kwargs: Additional Auth0-specific parameters
        """
        payload = {"members": user_ids, **kwargs}
        self.base_client._make_request("DELETE", f"/organizations/{org_id}/members", json=payload)

    def get_organization_member_roles(
        self, org_id: str, user_id: str, **kwargs
    ) -> list[dict[str, Any]]:
        """
        Get roles assigned to a member within an organization.

        Args:
            org_id: Organization ID
            user_id: User ID
            **kwargs: Additional Auth0-specific parameters

        Returns:
            List of role objects
        """
        return self.base_client._make_request(
            "GET", f"/organizations/{org_id}/members/{user_id}/roles", params=kwargs
        )

    def assign_organization_member_roles(
        self, org_id: str, user_id: str, role_ids: list[str], **kwargs
    ) -> None:
        """
        Assign roles to a member within an organization.

        Args:
            org_id: Organization ID
            user_id: User ID
            role_ids: List of role IDs to assign
            **kwargs: Additional Auth0-specific parameters
        """
        payload = {"roles": role_ids, **kwargs}
        self.base_client._make_request(
            "POST", f"/organizations/{org_id}/members/{user_id}/roles", json=payload
        )
