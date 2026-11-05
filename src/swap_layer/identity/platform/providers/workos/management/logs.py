"""
WorkOS audit log management operations.

Handles event/audit log access via the WorkOS Events API.
"""

from typing import TYPE_CHECKING, Any

from swap_layer.identity.platform.management._responses import object_list
from swap_layer.identity.platform.management.adapter import LogManagementAdapter

if TYPE_CHECKING:
    from .client import WorkOSManagementClient


class WorkOSLogManagement(LogManagementAdapter):
    """WorkOS audit log management implementation."""

    def __init__(self, base_client: "WorkOSManagementClient"):
        """Initialize with base management client.

        Args:
            base_client: WorkOSManagementClient instance
        """
        self.base_client = base_client

    def list_logs(
        self, page: int = 0, per_page: int = 50, query: str | None = None, **kwargs
    ) -> list[dict[str, Any]]:
        if page != 0 or query is not None:
            raise NotImplementedError("WorkOS events use cursor pagination and event-type filters")
        kwargs.setdefault("limit", per_page)
        return object_list(self.list_logs_page(**kwargs).get("data", []))

    def list_logs_page(
        self,
        organization_id: str | None = None,
        events: list[str] | None = None,
        limit: int = 50,
        **kwargs,
    ) -> dict[str, Any]:
        """List audit log events.

        Args:
            organization_id: Filter by organization
            events: Filter by event types
            limit: Number of results to return
            **kwargs: Additional parameters (before, after, order)

        Returns:
            Dict with 'data' (list of events) and 'listMetadata'
        """
        params: dict[str, Any] = {"limit": limit}
        if organization_id:
            params["organization_id"] = organization_id
        if events:
            params["events"] = events
        params.update(kwargs)
        return self.base_client._make_request("GET", "/events", params=params)

    def get_log(self, log_id: str) -> dict[str, Any]:
        """Get a specific log entry.

        Note: WorkOS events API doesn't support getting individual events by ID.

        Args:
            log_id: Log entry ID

        Raises:
            NotImplementedError: WorkOS doesn't support this operation
        """
        raise NotImplementedError("WorkOS does not support getting individual events by ID")

    def get_user_logs(self, user_id: str, page: int = 0, per_page: int = 50, **kwargs) -> list[dict[str, Any]]:
        """Get logs for a specific user.

        Args:
            user_id: User ID
            limit: Number of results
            **kwargs: Additional parameters

        Returns:
            Dict with user's log entries
        """
        # The Events API has no equivalent user filter. Returning all users'
        # events here would violate this method's promised boundary.
        raise NotImplementedError("WorkOS Events cannot be queried by user through this adapter")

    def filter_logs(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        action: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Filter logs by action.

        Note: WorkOS uses cursor-based pagination, not date ranges.

        Args:
            start_date: Start date (not supported)
            end_date: End date (not supported)
            action: Event action type
            **kwargs: Additional filter parameters

        Returns:
            Dict with filtered log entries
        """
        params: dict[str, Any] = {}
        if start_date is not None or end_date is not None:
            raise NotImplementedError("Date filtering is unavailable through this adapter")
        if action:
            params["events"] = [action]
        # WorkOS uses before/after cursor-based pagination, not date ranges
        params.update(kwargs)
        return self.base_client._make_request("GET", "/events", params=params)
