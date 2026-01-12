"""
WorkOS audit log management operations.

Handles event/audit log access via the WorkOS Events API.
"""

from typing import Any

from swap_layer.identity.platform.management.adapter import LogManagementAdapter


class WorkOSLogManagement(LogManagementAdapter):
    """WorkOS audit log management implementation."""

    def __init__(self, base_client):
        """Initialize with base management client.

        Args:
            base_client: WorkOSManagementClient instance
        """
        self.base_client = base_client

    def list_logs(
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
        params = {"limit": limit}
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

    def get_user_logs(self, user_id: str, limit: int = 50, **kwargs) -> dict[str, Any]:
        """Get logs for a specific user.

        Args:
            user_id: User ID
            limit: Number of results
            **kwargs: Additional parameters

        Returns:
            Dict with user's log entries
        """
        # Filter events related to the user
        user_events = [
            "user.created",
            "user.updated",
            "user.deleted",
            "authentication.email_verification_succeeded",
            "authentication.magic_auth_succeeded",
            "authentication.password_succeeded",
            "authentication.sso_succeeded",
        ]
        return self.list_logs(events=user_events, limit=limit, **kwargs)

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
        params = {}
        if action:
            params["events"] = [action]
        # WorkOS uses before/after cursor-based pagination, not date ranges
        params.update(kwargs)
        return self.base_client._make_request("GET", "/events", params=params)
