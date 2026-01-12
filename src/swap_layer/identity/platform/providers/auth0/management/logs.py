"""
Auth0 Log Management Implementation
"""

from typing import Any

from swap_layer.identity.platform.management.adapter import LogManagementAdapter


class Auth0LogManagement(LogManagementAdapter):
    """
    Auth0-specific implementation of audit log and event management operations.
    """

    def __init__(self, base_client):
        """
        Initialize with base client for shared functionality.

        Args:
            base_client: Auth0ManagementClient instance
        """
        self.base_client = base_client

    def list_logs(
        self,
        page: int = 0,
        per_page: int = 50,
        query: str | None = None,
        from_id: str | None = None,
        **kwargs,
    ) -> list[dict[str, Any]]:
        """
        List audit logs with pagination and optional filtering.

        Args:
            page: Page number (for offset pagination)
            per_page: Results per page
            query: Lucene query to filter logs
            from_id: Checkpoint ID for checkpoint-based pagination
            **kwargs: Additional Auth0-specific parameters

        Returns:
            List of log entry objects

        Example:
            >>> # Get failed login attempts
            >>> logs.list_logs(query='type:f AND date:[2024-01-01 TO 2024-12-31]')
        """
        params = {}

        # Checkpoint-based pagination (preferred for large datasets)
        if from_id:
            params["from"] = from_id
            params["take"] = per_page
        # Offset-based pagination
        else:
            params["page"] = page
            params["per_page"] = per_page

        if query:
            params["q"] = query

        params.update(kwargs)

        return self.base_client._make_request("GET", "/logs", params=params)

    def get_log(self, log_id: str) -> dict[str, Any]:
        """
        Get a specific log entry.

        Args:
            log_id: Log entry ID

        Returns:
            Log entry object
        """
        return self.base_client._make_request("GET", f"/logs/{log_id}")

    def get_user_logs(
        self, user_id: str, page: int = 0, per_page: int = 50, **kwargs
    ) -> list[dict[str, Any]]:
        """
        Get logs for a specific user.

        Args:
            user_id: Auth0 user ID
            page: Page number
            per_page: Results per page
            **kwargs: Additional Auth0-specific parameters

        Returns:
            List of log entries for the user
        """
        # Use Lucene query to filter by user
        query = f'user_id:"{user_id}"'
        return self.list_logs(page=page, per_page=per_page, query=query, **kwargs)

    def get_logs_by_type(
        self, log_type: str, page: int = 0, per_page: int = 50, **kwargs
    ) -> list[dict[str, Any]]:
        """
        Get logs by type.

        Args:
            log_type: Log type code (e.g., 's' for success login, 'f' for failed login)
            page: Page number
            per_page: Results per page
            **kwargs: Additional Auth0-specific parameters

        Returns:
            List of log entries

        Common log types:
            - 's': Success Login
            - 'f': Failed Login
            - 'w': Warnings During Login
            - 'du': Deleted User
            - 'fu': Failed User Update
            - 'fp': Failed Password Change
        """
        query = f"type:{log_type}"
        return self.list_logs(page=page, per_page=per_page, query=query, **kwargs)

    def get_logs_by_date_range(
        self, date_from: str, date_to: str, page: int = 0, per_page: int = 50, **kwargs
    ) -> list[dict[str, Any]]:
        """
        Get logs within a date range.

        Args:
            date_from: Start date (ISO 8601 format or YYYYMMDD)
            date_to: End date (ISO 8601 format or YYYYMMDD)
            page: Page number
            per_page: Results per page
            **kwargs: Additional Auth0-specific parameters

        Returns:
            List of log entries

        Example:
            >>> logs.get_logs_by_date_range('2024-01-01', '2024-01-31')
        """
        query = f"date:[{date_from} TO {date_to}]"
        return self.list_logs(page=page, per_page=per_page, query=query, **kwargs)
