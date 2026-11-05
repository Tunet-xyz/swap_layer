"""
WorkOS organization management operations.

Handles organization CRUD and membership management via the WorkOS Organizations API.
"""

from typing import TYPE_CHECKING, Any

from swap_layer.exceptions import SwapLayerError
from swap_layer.identity.platform.management._responses import object_list
from swap_layer.identity.platform.management.adapter import OrganizationManagementAdapter

if TYPE_CHECKING:
    from .client import WorkOSManagementClient


class WorkOSAPIError(SwapLayerError):
    """WorkOS API error."""

    def __init__(self, status_code: int | None, message: str, details: dict | None = None):
        super().__init__(f"WorkOS API Error ({status_code}): {message}")
        self.status_code = status_code
        self.details = details or {}


class WorkOSOrganizationManagement(OrganizationManagementAdapter):
    """WorkOS organization management implementation."""

    def __init__(self, base_client: "WorkOSManagementClient"):
        """Initialize with base management client.

        Args:
            base_client: WorkOSManagementClient instance
        """
        self.base_client = base_client

    def list_organizations(
        self, page: int = 0, per_page: int = 50, **kwargs
    ) -> list[dict[str, Any]]:
        """Return one page; cursor pagination is available through keyword arguments."""
        if page != 0:
            raise NotImplementedError("WorkOS uses cursor pagination; pass after or before")
        kwargs.setdefault("limit", per_page)
        return object_list(self.list_organizations_page(**kwargs).get("data", []))

    def list_organizations_page(
        self, domains: list[str] | None = None, limit: int = 50, **kwargs
    ) -> dict[str, Any]:
        """List organizations.

        Args:
            domains: Filter by domains
            limit: Number of results to return
            **kwargs: Additional query parameters

        Returns:
            Dict with 'data' (list of organizations) and 'listMetadata'
        """
        params: dict[str, Any] = {"limit": limit}
        if domains:
            params["domains"] = domains
        params.update(kwargs)
        return self.base_client._make_request("GET", "/organizations", params=params)

    def get_organization(self, org_id: str) -> dict[str, Any]:
        """Get organization by ID.

        Args:
            organization_id: WorkOS organization ID

        Returns:
            Organization object
        """
        return self.base_client._make_request("GET", f"/organizations/{org_id}")

    def create_organization(
        self, name: str, display_name: str | None = None, metadata: dict | None = None,
        *, domains: list[str] | None = None, **kwargs
    ) -> dict[str, Any]:
        """Create a new organization.

        Args:
            name: Organization name
            domains: List of domain names
            **kwargs: Additional properties (external_id, metadata, domain_data)

        Returns:
            Created organization object
        """
        data: dict[str, Any] = {"name": name}
        if display_name is not None:
            data["name"] = display_name
        if metadata is not None:
            data["metadata"] = metadata
        if domains:
            # Convert simple domain list to domain_data format
            data["domain_data"] = [{"domain": d, "state": "pending"} for d in domains]
        data.update(kwargs)
        return self.base_client._make_request("POST", "/organizations", json=data)

    def update_organization(
        self,
        org_id: str,
        name: str | None = None,
        display_name: str | None = None,
        metadata: dict | None = None,
        *,
        domains: list[str] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Update an existing organization.

        Args:
            organization_id: WorkOS organization ID
            name: Updated organization name
            domains: Updated list of domains
            **kwargs: Additional properties to update

        Returns:
            Updated organization object
        """
        data: dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if display_name is not None:
            data["name"] = display_name
        if metadata is not None:
            data["metadata"] = metadata
        if domains is not None:
            data["domain_data"] = [{"domain": d, "state": "pending"} for d in domains]
        data.update(kwargs)
        return self.base_client._make_request("PUT", f"/organizations/{org_id}", json=data)

    def delete_organization(self, org_id: str) -> None:
        """Delete an organization.

        Args:
            organization_id: WorkOS organization ID

        Returns:
            True if successful
        """
        self.base_client._make_request("DELETE", f"/organizations/{org_id}")

    def list_organization_members(
        self, org_id: str, page: int = 0, per_page: int = 50, **kwargs
    ) -> list[dict[str, Any]]:
        if page != 0:
            raise NotImplementedError("WorkOS uses cursor pagination; pass after or before")
        kwargs.setdefault("limit", per_page)
        return object_list(self.list_organization_members_page(org_id, **kwargs).get("data", []))

    def list_organization_members_page(
        self, organization_id: str, limit: int = 50, **kwargs
    ) -> dict[str, Any]:
        """List organization members.

        Args:
            organization_id: WorkOS organization ID
            limit: Number of results to return
            **kwargs: Additional query parameters

        Returns:
            Dict with organization membership data
        """
        params: dict[str, Any] = {"organization_id": organization_id, "limit": limit}
        params.update(kwargs)
        return self.base_client._make_request(
            "GET", "/user_management/organization_memberships", params=params
        )

    def add_organization_member(
        self, organization_id: str, user_id: str, role_slug: str | None = None
    ) -> dict[str, Any]:
        """Add a member to an organization.

        Args:
            organization_id: WorkOS organization ID
            user_id: WorkOS user ID
            role_slug: Role slug to assign

        Returns:
            Organization membership object
        """
        data: dict[str, Any] = {"organization_id": organization_id, "user_id": user_id}
        if role_slug:
            data["role_slug"] = role_slug
        return self.base_client._make_request(
            "POST", "/user_management/organization_memberships", json=data
        )

    def remove_organization_member(self, organization_id: str, user_id: str) -> bool:
        """Remove a member from an organization.

        Args:
            organization_id: WorkOS organization ID
            user_id: WorkOS user ID

        Returns:
            True if successful
        """
        memberships = self.list_organization_members_page(organization_id, user_id=user_id, limit=100)
        for membership in memberships.get("data", []):
            if membership.get("user_id") == user_id:
                membership_id = membership.get("id")
                self.base_client._make_request(
                    "DELETE", f"/user_management/organization_memberships/{membership_id}"
                )
                return True
        return False

    def add_organization_members(self, org_id: str, user_ids: list[str], **kwargs) -> None:
        for user_id in user_ids:
            self.add_organization_member(org_id, user_id, **kwargs)

    def remove_organization_members(self, org_id: str, user_ids: list[str], **kwargs) -> None:
        if kwargs:
            raise TypeError("Unsupported WorkOS membership removal options")
        for user_id in user_ids:
            if not self.remove_organization_member(org_id, user_id):
                raise WorkOSAPIError(404, "Organization membership not found")

    def update_organization_member_role(
        self, organization_id: str, user_id: str, role_slug: str
    ) -> dict[str, Any]:
        """Update organization member's role.

        Args:
            organization_id: WorkOS organization ID
            user_id: WorkOS user ID
            role_slug: New role slug

        Returns:
            Updated membership object

        Raises:
            WorkOSAPIError: If membership not found
        """
        memberships = self.list_organization_members_page(organization_id, user_id=user_id, limit=100)
        for membership in memberships.get("data", []):
            if membership.get("user_id") == user_id:
                membership_id = membership.get("id")
                data: dict[str, Any] = {"role_slug": role_slug}
                return self.base_client._make_request(
                    "PUT", f"/user_management/organization_memberships/{membership_id}", json=data
                )
        raise WorkOSAPIError(404, "Membership not found", {})
