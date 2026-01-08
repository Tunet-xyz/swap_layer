"""
WorkOS Management API implementation.

This package provides modular access to WorkOS management operations:
- Users: User CRUD via AuthKit
- Organizations: Organization and membership management
- Roles: Role listing and assignment
- Logs: Audit log access

Example:
    ```python
    from swap_layer.identity.platform.management.factory import get_management_client

    mgmt = get_management_client()
    user = mgmt.users.get_user("user_01H8...")
    ```
"""

from .client import WorkOSManagementClient

__all__ = ["WorkOSManagementClient"]
