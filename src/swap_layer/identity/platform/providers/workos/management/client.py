"""
WorkOS Management API client.

Provides unified access to all WorkOS management operations with
resilient HTTP handling and automatic retries.
"""

import logging
from typing import Any

from swap_layer.http import ResilientSession
from swap_layer.identity.platform.management.adapter import IdentityManagementClient
from swap_layer.identity.platform.providers.workos.management.logs import WorkOSLogManagement
from swap_layer.identity.platform.providers.workos.management.organizations import (
    WorkOSAPIError,
    WorkOSOrganizationManagement,
)
from swap_layer.identity.platform.providers.workos.management.roles import WorkOSRoleManagement
from swap_layer.identity.platform.providers.workos.management.users import WorkOSUserManagement

logger = logging.getLogger(__name__)


class WorkOSManagementClient(IdentityManagementClient):
    """WorkOS Management API client with automatic retries."""

    BASE_URL = "https://api.workos.com"

    def __init__(self, api_key: str):
        """Initialize WorkOS management client.

        Args:
            api_key: WorkOS API key
        """
        self.api_key = api_key
        self._session = ResilientSession(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
            max_retries=3,
        )
        self._users: WorkOSUserManagement | None = None
        self._organizations: WorkOSOrganizationManagement | None = None
        self._roles: WorkOSRoleManagement | None = None
        self._logs: WorkOSLogManagement | None = None

    @property
    def users(self) -> WorkOSUserManagement:
        """Get user management interface."""
        if self._users is None:
            self._users = WorkOSUserManagement(self)
        return self._users

    @property
    def organizations(self) -> WorkOSOrganizationManagement:
        """Get organization management interface."""
        if self._organizations is None:
            self._organizations = WorkOSOrganizationManagement(self)
        return self._organizations

    @property
    def roles(self) -> WorkOSRoleManagement:
        """Get role management interface."""
        if self._roles is None:
            self._roles = WorkOSRoleManagement(self)
        return self._roles

    @property
    def logs(self) -> WorkOSLogManagement:
        """Get log management interface."""
        if self._logs is None:
            self._logs = WorkOSLogManagement(self)
        return self._logs

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request to WorkOS API with automatic retries.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters

        Returns:
            API response data

        Raises:
            WorkOSAPIError: If API request fails after retries
        """
        if data is not None and json is not None:
            raise TypeError("Pass data or json, not both")
        try:
            response = self._session._make_request(
                method=method,
                endpoint=endpoint,
                json=json if json is not None else data,
                params=params,
            )
            payload = response.json() if response.content else {}
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object from WorkOS")
            return payload
        except Exception as e:
            error_msg = type(e).__name__
            status_code = None

            # Extract status code if available
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code

            logger.error(f"WorkOS API error: {error_msg}")
            raise WorkOSAPIError(
                message=f"WorkOS API request failed: {error_msg}",
                status_code=status_code,
            )
