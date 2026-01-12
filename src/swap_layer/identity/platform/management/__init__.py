"""
Identity Platform Management API

Provider-agnostic abstraction for administrative operations like user management,
organization management, role assignment, etc.

This is separate from authentication (OAuth/OIDC) which is handled by the
identity.platform module.
"""

from .adapter import (
    LogManagementAdapter,
    OrganizationManagementAdapter,
    RoleManagementAdapter,
    UserManagementAdapter,
)
from .factory import get_management_client

__all__ = [
    "UserManagementAdapter",
    "OrganizationManagementAdapter",
    "RoleManagementAdapter",
    "LogManagementAdapter",
    "get_management_client",
]
