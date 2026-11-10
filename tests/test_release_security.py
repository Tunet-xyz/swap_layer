"""Regression checks for storage boundaries and local MCP credential handling."""

import json
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from swap_layer.mcp.server import _check_storage, _get_config, _redact_config, _send_test_sms
from swap_layer.settings import SwapLayerSettings
from swap_layer.storage.adapter import StorageUploadError
from swap_layer.storage.providers.local import LocalFileStorageProvider
from swap_layer.storage.security import StorageSecurityContext


@pytest.mark.parametrize("key", ["../outside", "org/../../outside", "/outside", "C:/outside", "C:outside", r"org\..\outside", "file:stream", "file\x00name"])
def test_local_storage_rejects_escaping_keys(tmp_path, key):
    provider = LocalFileStorageProvider(str(tmp_path / "objects"))
    with pytest.raises(StorageUploadError):
        provider.upload_file(key, BytesIO(b"should not be written"))
    with pytest.raises(ValueError):
        provider.get_file_url(key)
    assert not list(provider.base_path.iterdir())


def test_local_storage_lifecycle(tmp_path):
    provider = LocalFileStorageProvider(str(tmp_path / "objects"))
    uploaded = provider.upload_file("org-a/docs/a.txt", BytesIO(b"hello"), metadata={"type": "text"})
    assert uploaded["size"] == 5
    assert provider.download_file("org-a/docs/a.txt") == b"hello"
    assert provider.get_file_metadata("org-a/docs/a.txt")["metadata"] == {"type": "text"}
    provider.copy_file("org-a/docs/a.txt", "org-a/docs/b.txt")
    provider.move_file("org-a/docs/b.txt", "org-a/docs/c.txt")
    assert {entry["file_path"] for entry in provider.list_files("org-a/")} == {"org-a/docs/a.txt", "org-a/docs/c.txt"}
    provider.delete_file("org-a/docs/c.txt")
    assert not provider.file_exists("org-a/docs/c.txt")


def test_local_storage_rejects_resolution_into_another_tenant(tmp_path):
    provider = LocalFileStorageProvider(str(tmp_path))
    with patch("swap_layer.storage.providers.local.Path.resolve", return_value=tmp_path / "org-b/private.txt"):
        with pytest.raises(StorageUploadError, match="junctions"):
            provider.upload_file("org-a/private.txt", BytesIO(b"changed"))


def test_local_storage_does_not_follow_symlinks(tmp_path):
    provider = LocalFileStorageProvider(str(tmp_path / "objects"))
    outside = tmp_path / "other-tenant"
    outside.mkdir()
    (outside / "private.txt").write_text("private")
    try:
        (provider.base_path / "link").symlink_to(outside, target_is_directory=True)
        (provider.base_path / "visible.txt").symlink_to(outside / "private.txt")
    except OSError as exc:
        pytest.skip(f"Host cannot create test symlinks: {exc.winerror if hasattr(exc, 'winerror') else exc.errno}")
    with pytest.raises(StorageUploadError):
        provider.upload_file("link/private.txt", BytesIO(b"changed"))
    assert (outside / "private.txt").read_text() == "private"
    assert provider.list_files() == []


@pytest.mark.parametrize("path", ["../org-b/a.txt", "nested/../../org-b/a.txt", "/org-b/a.txt", r"..\org-b\a.txt", "file:stream", "a\x00b"])
def test_tenant_paths_cannot_escape(path):
    context = StorageSecurityContext(organization_id="org-a", scope_format="tenants/{organization_id}")
    with pytest.raises(ValueError):
        context.scope_path(path)
    assert not context.validate_scoped_path(f"tenants/org-a/{path}")


@pytest.mark.parametrize("org", ["../org-b", "org-a/org-b", "org-a\n", "..", "/"])
def test_tenant_identity_is_one_safe_segment(org):
    with pytest.raises(ValueError):
        StorageSecurityContext(organization_id=org, scope_format="{organization_id}")


def test_scope_includes_organization_and_validates_prefix():
    with pytest.raises(ValueError):
        StorageSecurityContext(organization_id="org-a", scope_format="shared")
    context = StorageSecurityContext(organization_id="org-a", scope_format="tenants/{organization_id}")
    assert context.scope_path("docs/a.txt") == "tenants/org-a/docs/a.txt"
    assert context.validate_scoped_path("tenants/org-a/docs/a.txt")
    assert not context.validate_scoped_path("tenants/org-ab/docs/a.txt")


@pytest.mark.asyncio
async def test_mcp_redacts_nested_current_settings():
    settings = SwapLayerSettings(
        billing={"provider": "stripe", "stripe": {"secret_key": "sk_private-billing-value"}},
        identity={"provider": "workos", "workos_apps": {"default": {
            "api_key": "private-api-value", "client_id": "public-client", "cookie_password": "cHJpdmF0ZS1jb29raWUtcGFzc3dvcmQtMzItYnl0ZXM=",
        }}},
        verification={"stripe_secret_key": "private-verification-value"},
    )
    with patch("swap_layer.settings.get_swaplayer_settings", return_value=settings):
        result = await _get_config("all")
        single = await _get_config("billing")
    assert result["status"] == single["status"] == "success"
    serialized = json.dumps(result)
    assert "private-" not in serialized
    assert "cHJpdmF0ZS1jb29raWUtcGFzc3dvcmQtMzItYnl0ZXM=" not in serialized
    assert "public-client" in serialized
    assert single["config"]["provider"] == "stripe"
    assert _redact_config({"nested": [{"AWS_SECRET_ACCESS_KEY": "private", "provider": "kept"}]}) == {"nested": [{"provider": "kept"}]}


@pytest.mark.asyncio
async def test_mcp_does_not_echo_provider_exception_credentials():
    with patch("swap_layer.get_provider", side_effect=RuntimeError("credential=private-token")):
        result = await _send_test_sms("+15555551234", "test")
    assert "private-token" not in json.dumps(result)
    assert result["error_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_mcp_storage_probe_uses_storage_adapter():
    provider = Mock()
    with patch("swap_layer.get_provider", return_value=provider):
        result = await _check_storage(test_upload=True)
    assert result["test_upload"] == "success"
    assert result["test_cleanup"] == "deleted"
    filename, stream = provider.upload_file.call_args.args
    assert filename.startswith("swaplayer-mcp-check/")
    assert stream.getvalue() == b"SwapLayer MCP test file"
    provider.delete_file.assert_called_once_with(filename)


@pytest.mark.asyncio
async def test_mcp_storage_probe_reports_a_file_it_could_not_delete():
    provider = Mock()
    provider.delete_file.side_effect = RuntimeError("credential=private-token")
    with patch("swap_layer.get_provider", return_value=provider):
        result = await _check_storage(test_upload=True)
    assert result["test_upload"] == "success"
    assert result["test_cleanup"] == "failed"
    assert result["test_file"].startswith("swaplayer-mcp-check/")
    assert "private-token" not in json.dumps(result)


@pytest.mark.asyncio
async def test_mcp_storage_probe_skips_cleanup_after_a_failed_upload():
    provider = Mock()
    provider.upload_file.side_effect = RuntimeError("denied")
    with patch("swap_layer.get_provider", return_value=provider):
        result = await _check_storage(test_upload=True)
    assert result["test_upload"] == "failed"
    provider.delete_file.assert_not_called()


def test_auth0_management_requests_have_bounded_timeout():
    from swap_layer.identity.platform.providers.auth0.management import client as module

    response = Mock()
    response.json.return_value = {"access_token": "test-token", "expires_in": 3600}
    client = module.Auth0ManagementClient("developer")
    with patch.object(module.cache, "get", return_value=None), patch.object(module.cache, "set"), patch.object(module, "resilient_request", return_value=response) as post:
        assert client._get_management_token() == "test-token"
    assert post.call_args.kwargs["timeout"] == 30
    with patch.object(client, "_get_management_token", return_value="test-token"):
        session = client._get_session()
    assert session.timeout == 30


def test_no_module_is_shadowed_by_a_package():
    """A file x.py next to a package x/ can never be imported; neither may ship."""
    root = Path(__file__).parents[1] / "src" / "swap_layer"
    shadowed = [
        str(package.relative_to(root))
        for package in root.rglob("*")
        if package.is_dir() and (package / "__init__.py").exists() and package.with_suffix(".py").exists()
    ]
    assert shadowed == []
    assert not (root / "config.py").exists()
