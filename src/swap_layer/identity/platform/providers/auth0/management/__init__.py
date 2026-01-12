"""
Auth0 Management API

Modular implementation of Auth0 Management API v2 operations.
"""

from .client import Auth0ManagementClient
from .logs import Auth0LogManagement
from .organizations import Auth0OrganizationManagement
from .roles import Auth0RoleManagement
from .users import Auth0UserManagement

__all__ = [
    "Auth0ManagementClient",
    "Auth0UserManagement",
    "Auth0OrganizationManagement",
    "Auth0RoleManagement",
    "Auth0LogManagement",
]
