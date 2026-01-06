"""
Auth0 Management API

Modular implementation of Auth0 Management API v2 operations.
"""

from .client import Auth0ManagementClient
from .users import Auth0UserManagement
from .organizations import Auth0OrganizationManagement
from .roles import Auth0RoleManagement
from .logs import Auth0LogManagement

__all__ = [
    'Auth0ManagementClient',
    'Auth0UserManagement',
    'Auth0OrganizationManagement',
    'Auth0RoleManagement',
    'Auth0LogManagement',
]
