"""
WorkOS Management API client.

Provides unified access to all WorkOS management operations.
"""

import logging
from typing import Dict, Any, Optional

import requests

from swap_layer.identity.platform.management.adapter import IdentityManagementClient
from swap_layer.identity.platform.providers.workos.management.users import WorkOSUserManagement
from swap_layer.identity.platform.providers.workos.management.organizations import (
    WorkOSOrganizationManagement,
    WorkOSAPIError,
)
from swap_layer.identity.platform.providers.workos.management.roles import WorkOSRoleManagement
from swap_layer.identity.platform.providers.workos.management.logs import WorkOSLogManagement

logger = logging.getLogger(__name__)


class WorkOSManagementClient(IdentityManagementClient):
    """WorkOS Management API client."""

    BASE_URL = "https://api.workos.com"

    def __init__(self, api_key: str):
        """Initialize WorkOS management client.
        
        Args:
            api_key: WorkOS API key
        """
        self.api_key = api_key
        self._users = None
        self._organizations = None
        self._roles = None
        self._logs = None

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
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to WorkOS API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            
        Returns:
            API response data
            
        Raises:
            WorkOSAPIError: If API request fails
        """
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"WorkOS API error: {e.response.text}")
            raise WorkOSAPIError(
                message=f"WorkOS API request failed: {e.response.text}",
                status_code=e.response.status_code,
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"WorkOS API request failed: {str(e)}")
            raise WorkOSAPIError(
                message=f"WorkOS API request failed: {str(e)}",
                status_code=None,
            )
