"""
Storage Security Context - mirrors database RLS for object storage.

Provides tenant-scoped path enforcement, permission validation, and audit
logging for storage operations. Ensures all storage access respects
organizational boundaries without developers manually managing path prefixes.

Design Philosophy:
    Just as database RLS policies use SET LOCAL request.jwt.claims to scope
    queries to a tenant, StorageSecurityContext scopes all storage paths to
    the caller's organization/tenant namespace. Operations physically cannot
    escape the tenant boundary.

    JWT Verification:
        This module does NOT verify JWT signatures. JWT verification belongs
        at the API gateway / middleware layer — the same pattern used by
        database RLS. The RLSContext doesn't verify JWTs either; it receives
        pre-verified, resolved claims from the application layer.

        Trust model:
        - API gateway / middleware → verifies JWT signature + expiry
        - Application layer → resolves claims to (user_id, org_id, role)
        - Storage security context → enforces path scoping + permissions
        - Database RLS context → enforces row-level access

        Both storage and database contexts are downstream consumers of
        already-verified identity. Re-verifying would add latency without
        security benefit and couple the storage layer to a specific auth
        mechanism (JWT vs API key vs mTLS, etc.).

Usage:
    from swap_layer.storage.security import StorageSecurityContext, storage_context

    # Create context with caller identity
    ctx = StorageSecurityContext(
        user_id='auth0|123',
        organization_id='org-456',
        role='admin',
        platform='safety_az_central',
    )

    # Use with storage provider
    provider = get_storage_provider()
    with storage_context(provider, ctx) as scoped:
        # All paths are auto-prefixed: 'docs/report.pdf' -> 'orgs/org-456/docs/report.pdf'
        scoped.upload_file('docs/report.pdf', file_data, content_type='application/pdf')
        url = scoped.get_file_url('docs/report.pdf', expiration=timedelta(hours=1))
        scoped.delete_file('docs/report.pdf')

    # Without context (system operations) - requires explicit opt-in
    ctx = StorageSecurityContext.system_context()
    with storage_context(provider, ctx) as scoped:
        scoped.list_files(prefix='orgs/')  # Full access, logged as system operation
"""

import logging
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
from typing import Any, BinaryIO, Optional

logger = logging.getLogger(__name__)


__all__ = [
    'StorageSecurityContext',
    'StoragePermission',
    'ScopedStorageProvider',
    'storage_context',
    'validate_storage_context',
    'validate_path_segment',
]


class StoragePermission(Enum):
    """Permissions for storage operations."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"  # Bucket-level operations, ACL changes


# Role -> permission mapping (customizable per project)
DEFAULT_ROLE_PERMISSIONS: dict[str, set[StoragePermission]] = {
    'admin': {StoragePermission.READ, StoragePermission.WRITE, StoragePermission.DELETE, StoragePermission.ADMIN},
    'manager': {StoragePermission.READ, StoragePermission.WRITE, StoragePermission.DELETE},
    'member': {StoragePermission.READ, StoragePermission.WRITE},
    'viewer': {StoragePermission.READ},
    'system': {StoragePermission.READ, StoragePermission.WRITE, StoragePermission.DELETE, StoragePermission.ADMIN},
}


def validate_path_segment(segment: str) -> str:
    """
    Validate a path segment contains only safe characters.
    
    Prevents path traversal attacks (../) and injection via path components.
    
    Args:
        segment: Path segment to validate
        
    Returns:
        The validated segment
        
    Raises:
        ValueError: If segment contains unsafe characters
    """
    if '..' in segment:
        raise ValueError(f"Path traversal detected in segment: '{segment}'")
    
    if not re.match(r'^[a-zA-Z0-9_\-./]+$', segment):
        raise ValueError(
            f"Invalid path segment: '{segment}'. "
            f"Only alphanumeric characters, underscores, hyphens, dots, and slashes are allowed."
        )
    
    return segment


@dataclass
class StorageSecurityContext:
    """
    Security context for storage operations.
    
    Mirrors RLSContext from database security. Holds identity claims that
    determine path scoping and permission boundaries for storage operations.
    
    Path Scoping Strategy:
        All paths are automatically prefixed with the tenant namespace:
        - With org: 'orgs/{organization_id}/{original_path}'
        - System: No prefix (full access)
        
    Identity Resolution Strategy:
        Same as database RLS: Django/API gateway resolves identity and passes
        resolved values. No additional lookups needed in storage operations.
    
    Attributes:
        user_id: Authenticated user identifier
        organization_id: Tenant/organization boundary for path scoping
        role: User's role (determines permissions)
        platform: Application platform (e.g., 'safety_az_central')
        permissions: Explicit permissions (if None, derived from role)
        path_prefix: Custom path prefix (overrides default org-based prefix)
        is_system: Whether this is a system-level context (bypasses scoping)
        metadata: Additional context metadata for audit logging
    """
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    role: Optional[str] = None
    platform: Optional[str] = None
    permissions: Optional[set[StoragePermission]] = None
    path_prefix: Optional[str] = None
    is_system: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Configurable role->permission mapping
    role_permissions: dict[str, set[StoragePermission]] = field(
        default_factory=lambda: DEFAULT_ROLE_PERMISSIONS.copy()
    )
    
    def __post_init__(self):
        """Validate context on creation."""
        if not self.is_system:
            if not self.organization_id:
                raise ValueError(
                    "StorageSecurityContext requires organization_id for tenant isolation. "
                    "Use StorageSecurityContext.system_context() for system operations."
                )
    
    def get_permissions(self) -> set[StoragePermission]:
        """
        Get effective permissions for this context.
        
        Returns explicit permissions if set, otherwise derives from role.
        """
        if self.permissions is not None:
            return self.permissions
        
        if self.role:
            return self.role_permissions.get(self.role, set())
        
        # No role or permissions = read-only default
        return {StoragePermission.READ}
    
    def has_permission(self, permission: StoragePermission) -> bool:
        """Check if context has a specific permission."""
        return permission in self.get_permissions()
    
    def check_permission(self, permission: StoragePermission, operation: str = "") -> None:
        """
        Assert that the context has the required permission.
        
        Args:
            permission: Required permission
            operation: Description of the operation (for error messages)
            
        Raises:
            PermissionError: If permission is not granted
        """
        if not self.has_permission(permission):
            raise PermissionError(
                f"Storage operation '{operation}' requires {permission.value} permission. "
                f"User '{self.user_id}' with role '{self.role}' does not have this permission."
            )
    
    def scope_path(self, path: str) -> str:
        """
        Apply tenant-scoped path prefix.
        
        Args:
            path: Original path (e.g., 'documents/report.pdf')
            
        Returns:
            Scoped path (e.g., 'orgs/org-456/documents/report.pdf')
        """
        if self.is_system:
            return path
        
        # Use custom prefix if provided, otherwise derive from org
        prefix = self.path_prefix or f"orgs/{self.organization_id}"
        
        # Validate the prefix
        validate_path_segment(prefix)
        
        # Normalize: strip leading/trailing slashes
        prefix = prefix.strip('/')
        path = path.lstrip('/')
        
        return f"{prefix}/{path}"
    
    def validate_scoped_path(self, scoped_path: str) -> bool:
        """
        Validate that a scoped path is within this context's boundary.
        
        Args:
            scoped_path: Full scoped path to validate
            
        Returns:
            True if path is within boundary
        """
        if self.is_system:
            return True
        
        prefix = self.path_prefix or f"orgs/{self.organization_id}"
        prefix = prefix.strip('/')
        
        return scoped_path.startswith(f"{prefix}/")
    
    def to_audit_dict(self) -> dict[str, Any]:
        """Return context info for audit logging."""
        return {
            'user_id': self.user_id,
            'organization_id': self.organization_id,
            'role': self.role,
            'platform': self.platform,
            'is_system': self.is_system,
            'permissions': [p.value for p in self.get_permissions()],
            **self.metadata,
        }
    
    @classmethod
    def system_context(cls, reason: str = "system operation") -> 'StorageSecurityContext':
        """
        Create a system-level context that bypasses tenant scoping.
        
        Use sparingly. All system operations are logged.
        
        Args:
            reason: Reason for system access (logged for audit)
        """
        logger.warning(
            f"Creating system-level StorageSecurityContext - reason: {reason}"
        )
        return cls(
            user_id='system',
            role='system',
            is_system=True,
            metadata={'system_reason': reason},
        )


def validate_storage_context(
    context: StorageSecurityContext,
    required_platform: Optional[str] = None,
    required_permissions: Optional[set[StoragePermission]] = None,
    require_user: bool = False,
) -> None:
    """
    Validate that a storage security context meets minimum requirements.
    
    Mirrors validate_rls_context() from database security. Call this at the
    entry point of handlers/views to fail fast with clear errors rather than
    getting cryptic GCS errors downstream.
    
    This is NOT JWT verification (that belongs at the API gateway).
    This validates that the resolved, trusted context is well-formed and
    appropriate for the operation being performed.
    
    Args:
        context: StorageSecurityContext to validate
        required_platform: If provided, ensures context is for this platform
        required_permissions: If provided, ensures context has all of these
        require_user: If True, ensures user_id is set (not just org-level)
        
    Raises:
        ValueError: If context does not meet requirements
        PermissionError: If required permissions are missing
        
    Example:
        def upload_document(request, file):
            ctx = build_storage_context(request)
            validate_storage_context(
                ctx,
                required_platform='safety_az_central',
                required_permissions={StoragePermission.WRITE},
                require_user=True,
            )
            with storage_context(provider, ctx) as scoped:
                scoped.upload_file('documents/report.pdf', file)
    """
    if not context.is_system:
        if not context.organization_id:
            raise ValueError(
                "Storage context must have organization_id for tenant isolation"
            )
    
    if require_user and not context.user_id:
        raise ValueError(
            "Storage operation requires an authenticated user_id in the context"
        )
    
    if required_platform and context.platform != required_platform:
        raise ValueError(
            f"Storage operation requires platform '{required_platform}' "
            f"but context has '{context.platform}'"
        )
    
    if required_permissions:
        missing = required_permissions - context.get_permissions()
        if missing:
            missing_names = ', '.join(p.value for p in missing)
            raise PermissionError(
                f"Storage operation requires permissions: {missing_names}. "
                f"User '{context.user_id}' with role '{context.role}' is missing them."
            )


class ScopedStorageProvider:
    """
    Wraps a StorageProviderAdapter with security context enforcement.
    
    All operations are:
    1. Permission-checked against the context's role/permissions
    2. Path-scoped to the tenant's namespace
    3. Audit-logged with caller identity
    
    This is the storage equivalent of wrapping database operations with
    rls_context(conn, ctx).
    """
    
    def __init__(self, provider, context: StorageSecurityContext):
        """
        Args:
            provider: StorageProviderAdapter instance (GCS, S3, local, etc.)
            context: StorageSecurityContext with caller identity
        """
        self._provider = provider
        self._context = context
    
    @property
    def context(self) -> StorageSecurityContext:
        """Access the security context."""
        return self._context
    
    def _audit_log(self, operation: str, path: str, **extra):
        """Log storage operation for audit trail."""
        logger.info(
            f"Storage.{operation}: path='{path}' "
            f"user={self._context.user_id} "
            f"org={self._context.organization_id} "
            f"platform={self._context.platform}",
            extra={
                'storage_operation': operation,
                'storage_path': path,
                **self._context.to_audit_dict(),
                **extra,
            }
        )
    
    # ─── File Operations ───────────────────────────────────────────────
    
    def upload_file(
        self,
        file_path: str,
        file_data: BinaryIO,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
        public: bool = False,
    ) -> dict[str, Any]:
        """Upload a file with tenant scoping and permission check."""
        self._context.check_permission(StoragePermission.WRITE, 'upload_file')
        scoped_path = self._context.scope_path(file_path)
        self._audit_log('upload_file', scoped_path, content_type=content_type)
        
        # Inject security metadata
        security_metadata = {
            'uploaded_by': self._context.user_id or 'unknown',
            'organization_id': self._context.organization_id or 'system',
            'platform': self._context.platform or 'unknown',
        }
        if metadata:
            security_metadata.update(metadata)
        
        return self._provider.upload_file(
            file_path=scoped_path,
            file_data=file_data,
            content_type=content_type,
            metadata=security_metadata,
            public=public,
        )
    
    def upload_from_string(
        self,
        file_path: str,
        data: str | bytes,
        content_type: str = "text/plain",
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Upload string/bytes content with tenant scoping.
        
        Convenience method matching legacy upload_audio_file_to_bucket /
        archive_faunadb_document_as_json patterns.
        """
        self._context.check_permission(StoragePermission.WRITE, 'upload_from_string')
        scoped_path = self._context.scope_path(file_path)
        self._audit_log('upload_from_string', scoped_path, content_type=content_type)
        
        # Delegate to provider if it supports upload_from_string, otherwise adapt
        if hasattr(self._provider, 'upload_from_string'):
            return self._provider.upload_from_string(
                file_path=scoped_path,
                data=data,
                content_type=content_type,
                metadata=metadata,
            )
        
        # Fallback: convert to BinaryIO and use upload_file
        import io
        if isinstance(data, str):
            data = data.encode('utf-8')
        file_data = io.BytesIO(data)
        
        return self._provider.upload_file(
            file_path=scoped_path,
            file_data=file_data,
            content_type=content_type,
            metadata=metadata,
        )
    
    def download_file(self, file_path: str, destination: str | None = None) -> bytes:
        """Download a file with tenant scoping and permission check."""
        self._context.check_permission(StoragePermission.READ, 'download_file')
        scoped_path = self._context.scope_path(file_path)
        self._audit_log('download_file', scoped_path)
        return self._provider.download_file(scoped_path, destination)
    
    def download_as_bytes(self, file_path: str) -> bytes:
        """Download file content as bytes (convenience method)."""
        self._context.check_permission(StoragePermission.READ, 'download_as_bytes')
        scoped_path = self._context.scope_path(file_path)
        self._audit_log('download_as_bytes', scoped_path)
        
        if hasattr(self._provider, 'download_as_bytes'):
            return self._provider.download_as_bytes(scoped_path)
        return self._provider.download_file(scoped_path)
    
    def download_as_text(self, file_path: str, encoding: str = 'utf-8') -> str:
        """Download file content as text string (convenience method)."""
        self._context.check_permission(StoragePermission.READ, 'download_as_text')
        scoped_path = self._context.scope_path(file_path)
        self._audit_log('download_as_text', scoped_path)
        
        if hasattr(self._provider, 'download_as_text'):
            return self._provider.download_as_text(scoped_path, encoding=encoding)
        return self._provider.download_file(scoped_path).decode(encoding)
    
    def delete_file(self, file_path: str) -> dict[str, Any]:
        """Delete a file with tenant scoping and permission check."""
        self._context.check_permission(StoragePermission.DELETE, 'delete_file')
        scoped_path = self._context.scope_path(file_path)
        self._audit_log('delete_file', scoped_path)
        return self._provider.delete_file(scoped_path)
    
    def delete_files(self, file_paths: list[str]) -> dict[str, Any]:
        """Delete multiple files with tenant scoping and permission check."""
        self._context.check_permission(StoragePermission.DELETE, 'delete_files')
        scoped_paths = [self._context.scope_path(p) for p in file_paths]
        self._audit_log('delete_files', str(scoped_paths))
        return self._provider.delete_files(scoped_paths)
    
    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists with tenant scoping."""
        self._context.check_permission(StoragePermission.READ, 'file_exists')
        scoped_path = self._context.scope_path(file_path)
        return self._provider.file_exists(scoped_path)
    
    def get_file_metadata(self, file_path: str) -> dict[str, Any]:
        """Get file metadata with tenant scoping."""
        self._context.check_permission(StoragePermission.READ, 'get_file_metadata')
        scoped_path = self._context.scope_path(file_path)
        self._audit_log('get_file_metadata', scoped_path)
        return self._provider.get_file_metadata(scoped_path)
    
    def list_files(
        self, prefix: str | None = None, max_results: int = 1000
    ) -> list[dict[str, Any]]:
        """List files within tenant scope."""
        self._context.check_permission(StoragePermission.READ, 'list_files')
        
        # Scope the prefix to the tenant
        if prefix:
            scoped_prefix = self._context.scope_path(prefix)
        else:
            # List all files within the tenant namespace
            scoped_prefix = self._context.scope_path('')
        
        self._audit_log('list_files', scoped_prefix)
        return self._provider.list_files(prefix=scoped_prefix, max_results=max_results)
    
    # ─── URL Generation ────────────────────────────────────────────────
    
    def get_file_url(
        self, file_path: str, expiration: timedelta | None = None
    ) -> str:
        """Get a (signed) URL for a file with tenant scoping."""
        self._context.check_permission(StoragePermission.READ, 'get_file_url')
        scoped_path = self._context.scope_path(file_path)
        self._audit_log('get_file_url', scoped_path)
        return self._provider.get_file_url(scoped_path, expiration)
    
    def generate_presigned_upload_url(
        self,
        file_path: str,
        content_type: str | None = None,
        expiration: timedelta = timedelta(hours=1),
    ) -> dict[str, Any]:
        """Generate a presigned upload URL with tenant scoping."""
        self._context.check_permission(StoragePermission.WRITE, 'generate_presigned_upload_url')
        scoped_path = self._context.scope_path(file_path)
        self._audit_log('generate_presigned_upload_url', scoped_path)
        return self._provider.generate_presigned_upload_url(
            scoped_path, content_type, expiration
        )
    
    # ─── Bulk Operations ───────────────────────────────────────────────
    
    def copy_file(self, source_path: str, destination_path: str) -> dict[str, Any]:
        """Copy a file within tenant scope."""
        self._context.check_permission(StoragePermission.WRITE, 'copy_file')
        scoped_source = self._context.scope_path(source_path)
        scoped_dest = self._context.scope_path(destination_path)
        self._audit_log('copy_file', f"{scoped_source} -> {scoped_dest}")
        return self._provider.copy_file(scoped_source, scoped_dest)
    
    def move_file(self, source_path: str, destination_path: str) -> dict[str, Any]:
        """Move/rename a file within tenant scope."""
        self._context.check_permission(StoragePermission.WRITE, 'move_file')
        self._context.check_permission(StoragePermission.DELETE, 'move_file')
        scoped_source = self._context.scope_path(source_path)
        scoped_dest = self._context.scope_path(destination_path)
        self._audit_log('move_file', f"{scoped_source} -> {scoped_dest}")
        return self._provider.move_file(scoped_source, scoped_dest)


@contextmanager
def storage_context(
    provider,
    context: Optional[StorageSecurityContext] = None,
):
    """
    Context manager that wraps a storage provider with security enforcement.
    
    Mirrors rls_context(conn, ctx) from database security.
    
    Usage:
        provider = get_storage_provider()
        ctx = StorageSecurityContext(
            user_id='auth0|123',
            organization_id='org-456',
            role='admin',
        )
        with storage_context(provider, ctx) as scoped:
            scoped.upload_file('docs/report.pdf', file_data)
    
    Args:
        provider: StorageProviderAdapter instance
        context: StorageSecurityContext (if None, system context is used with warning)
    
    Yields:
        ScopedStorageProvider with security enforcement
    """
    if context is None:
        logger.warning(
            "Storage operation without security context - "
            "ensure this is intentional (e.g., system maintenance job)"
        )
        context = StorageSecurityContext.system_context(reason="no context provided")
    
    logger.debug(
        f"Storage security context active: "
        f"user={context.user_id}, org={context.organization_id}, "
        f"role={context.role}, platform={context.platform}"
    )
    
    scoped = ScopedStorageProvider(provider, context)
    
    try:
        yield scoped
    except PermissionError:
        logger.error(
            f"Storage permission denied: user={context.user_id}, "
            f"org={context.organization_id}, role={context.role}"
        )
        raise
    except Exception as e:
        logger.error(
            f"Storage operation error: {e} "
            f"(user={context.user_id}, org={context.organization_id})"
        )
        raise
    finally:
        logger.debug(
            f"Storage security context released: "
            f"user={context.user_id}, org={context.organization_id}"
        )
