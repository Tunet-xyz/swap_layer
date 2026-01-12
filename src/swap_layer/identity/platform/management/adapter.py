"""
Abstract base classes for identity management operations.

These adapters define the interface for administrative operations across
different identity providers (Auth0, WorkOS, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any


class UserManagementAdapter(ABC):
    """
    Abstract base class for user management operations.

    Provides CRUD operations for users across different identity providers.
    """

    @abstractmethod
    def list_users(
        self, page: int = 0, per_page: int = 50, search_query: str | None = None, **kwargs
    ) -> list[dict[str, Any]]:
        """
        List users with pagination and optional search.

        Args:
            page: Page number (0-indexed)
            per_page: Results per page
            search_query: Provider-specific search query
            **kwargs: Additional provider-specific parameters

        Returns:
            List of user objects
        """
        pass

    @abstractmethod
    def get_user(self, user_id: str) -> dict[str, Any]:
        """
        Get a specific user by ID.

        Args:
            user_id: Provider-specific user ID

        Returns:
            User object
        """
        pass

    @abstractmethod
    def create_user(
        self,
        email: str,
        password: str | None = None,
        email_verified: bool = False,
        metadata: dict | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Create a new user.

        Args:
            email: User email
            password: User password (if applicable)
            email_verified: Whether email is verified
            metadata: User metadata
            **kwargs: Additional provider-specific fields

        Returns:
            Created user object
        """
        pass

    @abstractmethod
    def update_user(
        self, user_id: str, email: str | None = None, metadata: dict | None = None, **kwargs
    ) -> dict[str, Any]:
        """
        Update an existing user.

        Args:
            user_id: Provider-specific user ID
            email: New email
            metadata: Metadata to merge
            **kwargs: Additional fields to update

        Returns:
            Updated user object
        """
        pass

    @abstractmethod
    def delete_user(self, user_id: str) -> None:
        """
        Delete a user.

        Args:
            user_id: Provider-specific user ID
        """
        pass

    @abstractmethod
    def search_users(self, query: str, per_page: int = 50, **kwargs) -> list[dict[str, Any]]:
        """
        Search users using provider-specific query syntax.

        Args:
            query: Search query
            per_page: Results per page
            **kwargs: Additional provider-specific parameters

        Returns:
            List of matching users
        """
        pass


class OrganizationManagementAdapter(ABC):
    """
    Abstract base class for organization/tenant management.

    Supports multi-tenant/B2B scenarios where users belong to organizations.
    """

    @abstractmethod
    def list_organizations(
        self, page: int = 0, per_page: int = 50, **kwargs
    ) -> list[dict[str, Any]]:
        """
        List organizations with pagination.

        Args:
            page: Page number (0-indexed)
            per_page: Results per page
            **kwargs: Additional provider-specific parameters

        Returns:
            List of organization objects
        """
        pass

    @abstractmethod
    def get_organization(self, org_id: str) -> dict[str, Any]:
        """
        Get organization details.

        Args:
            org_id: Organization ID

        Returns:
            Organization object
        """
        pass

    @abstractmethod
    def create_organization(
        self, name: str, display_name: str | None = None, metadata: dict | None = None, **kwargs
    ) -> dict[str, Any]:
        """
        Create a new organization.

        Args:
            name: Organization name/slug
            display_name: Display name
            metadata: Organization metadata
            **kwargs: Additional provider-specific fields

        Returns:
            Created organization object
        """
        pass

    @abstractmethod
    def update_organization(
        self,
        org_id: str,
        name: str | None = None,
        display_name: str | None = None,
        metadata: dict | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Update an organization.

        Args:
            org_id: Organization ID
            name: New name/slug
            display_name: New display name
            metadata: Metadata to merge
            **kwargs: Additional fields to update

        Returns:
            Updated organization object
        """
        pass

    @abstractmethod
    def delete_organization(self, org_id: str) -> None:
        """
        Delete an organization.

        Args:
            org_id: Organization ID
        """
        pass

    @abstractmethod
    def list_organization_members(
        self, org_id: str, page: int = 0, per_page: int = 50, **kwargs
    ) -> list[dict[str, Any]]:
        """
        List members of an organization.

        Args:
            org_id: Organization ID
            page: Page number
            per_page: Results per page
            **kwargs: Additional provider-specific parameters

        Returns:
            List of member objects
        """
        pass

    @abstractmethod
    def add_organization_members(self, org_id: str, user_ids: list[str], **kwargs) -> None:
        """
        Add members to an organization.

        Args:
            org_id: Organization ID
            user_ids: List of user IDs to add
            **kwargs: Additional provider-specific parameters
        """
        pass

    @abstractmethod
    def remove_organization_members(self, org_id: str, user_ids: list[str], **kwargs) -> None:
        """
        Remove members from an organization.

        Args:
            org_id: Organization ID
            user_ids: List of user IDs to remove
            **kwargs: Additional provider-specific parameters
        """
        pass


class RoleManagementAdapter(ABC):
    """
    Abstract base class for role and permission management.

    Supports RBAC (Role-Based Access Control) across identity providers.
    """

    @abstractmethod
    def list_roles(self, page: int = 0, per_page: int = 50, **kwargs) -> list[dict[str, Any]]:
        """
        List all available roles.

        Args:
            page: Page number
            per_page: Results per page
            **kwargs: Additional provider-specific parameters

        Returns:
            List of role objects
        """
        pass

    @abstractmethod
    def get_role(self, role_id: str) -> dict[str, Any]:
        """
        Get role details.

        Args:
            role_id: Role ID

        Returns:
            Role object
        """
        pass

    @abstractmethod
    def get_user_roles(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get roles assigned to a user.

        Args:
            user_id: User ID

        Returns:
            List of role objects
        """
        pass

    @abstractmethod
    def assign_user_roles(self, user_id: str, role_ids: list[str], **kwargs) -> None:
        """
        Assign roles to a user.

        Args:
            user_id: User ID
            role_ids: List of role IDs to assign
            **kwargs: Additional provider-specific parameters
        """
        pass

    @abstractmethod
    def remove_user_roles(self, user_id: str, role_ids: list[str], **kwargs) -> None:
        """
        Remove roles from a user.

        Args:
            user_id: User ID
            role_ids: List of role IDs to remove
            **kwargs: Additional provider-specific parameters
        """
        pass

    @abstractmethod
    def get_user_permissions(self, user_id: str) -> list[dict[str, Any]]:
        """
        Get permissions for a user (may be derived from roles).

        Args:
            user_id: User ID

        Returns:
            List of permission objects
        """
        pass


class LogManagementAdapter(ABC):
    """
    Abstract base class for audit log and event management.

    Provides access to authentication events, admin actions, and audit trails.
    """

    @abstractmethod
    def list_logs(
        self, page: int = 0, per_page: int = 50, query: str | None = None, **kwargs
    ) -> list[dict[str, Any]]:
        """
        List audit logs with pagination and optional filtering.

        Args:
            page: Page number
            per_page: Results per page
            query: Provider-specific query/filter
            **kwargs: Additional provider-specific parameters

        Returns:
            List of log entry objects
        """
        pass

    @abstractmethod
    def get_log(self, log_id: str) -> dict[str, Any]:
        """
        Get a specific log entry.

        Args:
            log_id: Log entry ID

        Returns:
            Log entry object
        """
        pass

    @abstractmethod
    def get_user_logs(
        self, user_id: str, page: int = 0, per_page: int = 50, **kwargs
    ) -> list[dict[str, Any]]:
        """
        Get logs for a specific user.

        Args:
            user_id: User ID
            page: Page number
            per_page: Results per page
            **kwargs: Additional provider-specific parameters

        Returns:
            List of log entries for the user
        """
        pass


class IdentityManagementClient(ABC):
    """
    Composite client that provides access to all management capabilities.

    This is the main entry point for identity management operations.
    It composes the individual adapters for users, organizations, roles, and logs.
    """

    @property
    @abstractmethod
    def users(self) -> UserManagementAdapter:
        """Access to user management operations."""
        pass

    @property
    @abstractmethod
    def organizations(self) -> OrganizationManagementAdapter:
        """Access to organization management operations."""
        pass

    @property
    @abstractmethod
    def roles(self) -> RoleManagementAdapter:
        """Access to role management operations."""
        pass

    @property
    @abstractmethod
    def logs(self) -> LogManagementAdapter:
        """Access to log management operations."""
        pass
