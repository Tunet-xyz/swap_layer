"""Storage security contexts: identity segments, permissions, system access and uploads."""

import dataclasses
from io import BytesIO
from unittest.mock import Mock

import pytest

from swap_layer.storage.providers.local import LocalFileStorageProvider
from swap_layer.storage.security import (
    DEFAULT_ROLE_PERMISSIONS,
    StoragePermission,
    StorageSecurityContext,
    storage_context,
    validate_path_segment,
)

ALL_PERMISSIONS = set(StoragePermission)


def tenant(org="org-a", role="member", **kwargs):
    return StorageSecurityContext(
        organization_id=org, role=role, scope_format="tenants/{organization_id}", **kwargs
    )


@pytest.mark.parametrize(
    "value", [".", "...", ".hidden", "trailing.", "a..b", "a/b", "org a", "org\n", "\\org"]
)
def test_identity_fields_must_be_plain_segments(value):
    with pytest.raises(ValueError, match="safe single path segments"):
        StorageSecurityContext(organization_id=value, scope_format="tenants/{organization_id}")
    with pytest.raises(ValueError, match="safe single path segments"):
        tenant(platform=value)
    with pytest.raises(ValueError, match="safe single path segments"):
        tenant(role=value)


@pytest.mark.parametrize("value", ["org-456", "org.example", "ORG_1", "a.b-c_d"])
def test_identity_fields_accept_plain_segments(value):
    context = StorageSecurityContext(organization_id=value, scope_format="tenants/{organization_id}")
    assert context.scope_path("x.txt") == f"tenants/{value}/x.txt"


def test_dot_organization_cannot_reach_other_tenants(tmp_path):
    provider = LocalFileStorageProvider(str(tmp_path))
    with storage_context(provider, tenant("org-999", role="admin")) as scoped:
        scoped.upload_file("secret.txt", BytesIO(b"other tenant"))
    with pytest.raises(ValueError):
        StorageSecurityContext(organization_id=".", role="admin", scope_format="tenants/{organization_id}")
    with storage_context(provider, tenant("org-a", role="admin")) as scoped:
        assert scoped.list_files() == []
        with pytest.raises(ValueError):
            scoped.download_file("../org-999/secret.txt")


@pytest.mark.parametrize("prefix", ["tenants/./x", "tenants/../x", "tenants//x", ".", "./x", "x/."])
def test_prefix_rejects_empty_and_dot_segments(prefix):
    with pytest.raises(ValueError):
        validate_path_segment(prefix)


def test_prefix_accepts_nested_segments():
    assert validate_path_segment("/tenants/org-a/data/") == "/tenants/org-a/data/"


def test_scope_with_unset_placeholder_fails_closed():
    context = StorageSecurityContext(
        organization_id="org-a", role="member", scope_format="tenants/{platform}/{organization_id}"
    )
    with pytest.raises(ValueError):
        context.scope_path("x.txt")
    with_platform = dataclasses.replace(context, platform="web")
    assert with_platform.scope_path("x.txt") == "tenants/web/org-a/x.txt"


@pytest.mark.parametrize("role", [None, "system", "unknown", "Admin"])
def test_missing_and_unknown_roles_have_no_permissions(role):
    context = tenant(role=role)
    assert context.get_permissions() == set()
    with pytest.raises(PermissionError):
        context.check_permission(StoragePermission.READ, "download_file")


def test_known_roles_and_explicit_permissions():
    assert tenant(role="viewer").get_permissions() == {StoragePermission.READ}
    assert tenant(role="member").get_permissions() == {StoragePermission.READ, StoragePermission.WRITE}
    assert tenant(role="admin").get_permissions() == ALL_PERMISSIONS
    explicit = tenant(role="admin", permissions={StoragePermission.READ})
    assert explicit.get_permissions() == {StoragePermission.READ}
    custom = tenant(role="system", role_permissions={"system": {StoragePermission.READ}})
    assert custom.get_permissions() == {StoragePermission.READ}


def test_role_mapping_is_copied_per_context():
    first = tenant(role="member")
    first.role_permissions["member"].add(StoragePermission.ADMIN)
    first.get_permissions().add(StoragePermission.DELETE)
    assert StoragePermission.DELETE not in first.get_permissions()
    assert StoragePermission.ADMIN not in DEFAULT_ROLE_PERMISSIONS["member"]
    assert tenant(role="member").get_permissions() == {StoragePermission.READ, StoragePermission.WRITE}


def test_system_access_requires_system_context():
    with pytest.raises(ValueError, match="system_context"):
        StorageSecurityContext(is_system=True)
    with pytest.raises(ValueError, match="system_context"):
        StorageSecurityContext(organization_id="org-a", scope_format="{organization_id}", is_system=True)
    system = StorageSecurityContext.system_context(reason="maintenance")
    assert system.is_system
    assert system.get_permissions() == ALL_PERMISSIONS
    assert system.scope_path("tenants/org-a/x.txt") == "tenants/org-a/x.txt"
    with pytest.raises(ValueError, match="system_context"):
        dataclasses.replace(system, metadata={})
    with pytest.raises(ValueError, match="system_context"):
        StorageSecurityContext(is_system=True)


def test_contexts_are_immutable_after_validation():
    context = tenant()
    with pytest.raises(dataclasses.FrozenInstanceError):
        context.organization_id = "."  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        context.is_system = True  # type: ignore[misc]


def test_public_upload_requires_admin():
    provider = Mock()
    with storage_context(provider, tenant(role="member")) as scoped:
        scoped.upload_file("a.txt", BytesIO(b"a"))
        with pytest.raises(PermissionError):
            scoped.upload_file("b.txt", BytesIO(b"b"), public=True)
    assert provider.upload_file.call_count == 1
    assert provider.upload_file.call_args.kwargs["public"] is False
    with storage_context(provider, tenant(role="admin")) as scoped:
        scoped.upload_file("c.txt", BytesIO(b"c"), public=True)
    assert provider.upload_file.call_args.kwargs["public"] is True
    assert provider.upload_file.call_args.kwargs["file_path"] == "tenants/org-a/c.txt"


def test_upload_metadata_cannot_replace_security_metadata():
    provider = Mock()
    context = tenant(role="member", user_id="user-1", platform="web")
    with storage_context(provider, context) as scoped:
        scoped.upload_file(
            "a.txt",
            BytesIO(b"a"),
            metadata={"organization_id": "org-b", "uploaded_by": "someone", "label": "kept"},
        )
    assert provider.upload_file.call_args.kwargs["metadata"] == {
        "organization_id": "org-a",
        "uploaded_by": "user-1",
        "platform": "web",
        "label": "kept",
    }


def test_audit_metadata_cannot_replace_identity_fields():
    context = tenant(user_id="user-1", metadata={"user_id": "someone", "request_id": "r-1"})
    audit = context.to_audit_dict()
    assert audit["user_id"] == "user-1"
    assert audit["request_id"] == "r-1"
    assert audit["permissions"] == ["read", "write"]
