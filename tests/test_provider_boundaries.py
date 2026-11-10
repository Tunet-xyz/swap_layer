"""Exercise provider adapters through their common interface without live accounts."""

import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from swap_layer.exceptions import ErrorContext
from swap_layer.settings import SwapLayerSettings
from swap_layer.storage.providers.local import LocalFileStorageProvider
from swap_layer.storage.security import StorageSecurityContext, storage_context


def test_scoped_storage_requires_explicit_context(tmp_path):
    provider = LocalFileStorageProvider(str(tmp_path))
    with pytest.raises(ValueError, match="explicit"):
        with storage_context(provider):
            pytest.fail("Missing context must not grant system access")


def test_tenant_storage_lifecycle_and_permissions(tmp_path):
    provider = LocalFileStorageProvider(str(tmp_path))
    member = StorageSecurityContext(organization_id="a", scope_format="{organization_id}", role="member")
    other = StorageSecurityContext(organization_id="b", scope_format="{organization_id}", role="admin")
    with storage_context(provider, member) as scoped:
        scoped.upload_file("report.txt", BytesIO(b"private"))
        assert scoped.download_as_text("report.txt") == "private"
        with pytest.raises(PermissionError):
            scoped.delete_file("report.txt")
    with storage_context(provider, other) as scoped:
        assert scoped.list_files() == []
        assert not scoped.file_exists("report.txt")


def test_error_context_omits_exception_inputs_and_nested_list_secrets():
    output = ErrorContext.build_config_error_context(
        ValueError("private-input-value"), {"apps": [{"api_key": "private-key-value", "name": "public"}]}
    )
    assert "private-" not in output
    assert "public" in output


def test_settings_validation_does_not_print_input_secrets():
    with pytest.raises(ValueError) as exc:
        SwapLayerSettings(identity={"provider": "unknown", "client_secret": "private-secret"})
    assert "private-secret" not in str(exc.value)


def test_workos_factory_and_all_management_interfaces_are_constructible():
    pytest.importorskip("workos")
    from swap_layer.identity.platform.management.factory import get_management_client

    settings = SwapLayerSettings(identity={"workos_apps": {"default": {
        "api_key": "fixture-key", "client_id": "fixture-client", "cookie_password": "c3dhcC1sYXllci10ZXN0LWNvb2tpZS1rZXktMzJieSE=",
    }}})
    with patch("swap_layer.settings.get_swaplayer_settings", return_value=settings):
        client = get_management_client()
    assert all((client.users, client.organizations, client.roles, client.logs))


def test_workos_json_transport_and_user_adapter_contract():
    from swap_layer.identity.platform.providers.workos.management.client import (
        WorkOSManagementClient,
    )

    client = WorkOSManagementClient("fixture-key")
    response = Mock(content=b"json")
    response.json.return_value = {"id": "user-fixture"}
    with patch.object(client._session, "_make_request", return_value=response) as request:
        result = client.users.create_user("user@example.com", None, True, {"tier": "test"})
    assert result == {"id": "user-fixture"}
    assert request.call_args.kwargs["json"]["metadata"] == {"tier": "test"}
    with patch.object(client, "_make_request", return_value={"data": [{"id": "user-fixture"}]}) as request:
        assert client.users.list_users(per_page=7) == [{"id": "user-fixture"}]
        assert request.call_args.kwargs["params"]["limit"] == 7
    with pytest.raises(NotImplementedError, match="cursor"):
        client.users.list_users(page=1)


def test_workos_bulk_memberships_and_unsupported_user_log_filter():
    from swap_layer.identity.platform.providers.workos.management.client import (
        WorkOSManagementClient,
    )

    client = WorkOSManagementClient("fixture-key")
    with patch.object(client.organizations, "add_organization_member") as add:
        client.organizations.add_organization_members("org-fixture", ["user-a", "user-b"])
    assert add.call_count == 2
    with pytest.raises(NotImplementedError, match="queried by user"):
        client.logs.get_user_logs("user-a")


def test_auth0_rejects_wrong_response_shapes():
    from swap_layer.identity.platform.providers.auth0.management.client import Auth0ManagementClient

    client = Auth0ManagementClient("developer")
    with patch.object(client, "_make_request", return_value=[{"user_id": "fixture"}]):
        assert client.users.list_users() == [{"user_id": "fixture"}]
        with pytest.raises(ValueError, match="JSON object"):
            client.users.get_user("fixture")
    with patch.object(client, "_make_request", return_value={"unexpected": "object"}):
        with pytest.raises(ValueError, match="array"):
            client.users.list_users()
    with patch.object(client, "_make_request", return_value=42):
        assert client.get_stats() == 42


def test_stripe_promotion_uses_current_sdk_shape():
    stripe = pytest.importorskip("stripe")
    from swap_layer.billing.providers.stripe import StripePaymentProvider

    provider = StripePaymentProvider(secret_key="sk_test_fixture")
    response = stripe.PromotionCode.construct_from({
        "id": "promo_fixture", "code": "FIXTURE", "active": True,
        "promotion": {"type": "coupon", "coupon": "coupon_fixture"}, "metadata": {},
    }, None)
    with patch.object(provider._client.v1.promotion_codes, "create", return_value=response) as create:
        result = provider.create_promotion_code("coupon_fixture")
    assert result["coupon_id"] == "coupon_fixture"
    assert create.call_args.kwargs["params"]["promotion"] == {"type": "coupon", "coupon": "coupon_fixture"}


def test_stripe_adapter_positional_idempotency_key():
    pytest.importorskip("stripe")
    from swap_layer.billing.providers.stripe import StripePaymentProvider

    provider = StripePaymentProvider(secret_key="sk_test_fixture")
    with patch.object(provider._client.v1.payment_intents, "create", return_value=Mock()) as create:
        provider.create_payment_intent(100, "gbp", None, None, None, "fixture-idempotency")
    assert create.call_args.kwargs["options"] == {"idempotency_key": "fixture-idempotency"}


def test_gcs_settings_reach_the_native_provider():
    from swap_layer.storage.factory import get_storage_provider

    settings = SwapLayerSettings(storage={"provider": "gcs", "bucket_name": "fixture-bucket", "project_id": "fixture-project"})
    with patch("swap_layer.storage.factory.get_swaplayer_settings", return_value=settings), patch("swap_layer.storage.providers.gcs.client._get_storage_client") as sdk:
        provider = get_storage_provider()
        assert provider.client is sdk.return_value
    assert provider.bucket_name == "fixture-bucket"
    sdk.assert_called_once_with(None, "fixture-project")


def test_sns_configuration_and_send_use_the_current_adapter():
    pytest.importorskip("boto3")
    from swap_layer.communications.sms.factory import get_sms_provider

    settings = SwapLayerSettings(communications={"sms": {"provider": "sns", "sns": {
        "region_name": "eu-west-2", "sender_id": "Fixture",
    }}})
    with patch("swap_layer.communications.sms.factory.get_swaplayer_settings", return_value=settings), patch("boto3.client") as sdk:
        sdk.return_value.publish.return_value = {"MessageId": "fixture-message"}
        provider = get_sms_provider()
        result = provider.send_sms("+15555551234", "fixture")
    assert result["message_id"] == "fixture-message"
    assert sdk.call_args.kwargs["region_name"] == "eu-west-2"
    assert sdk.return_value.publish.call_args.kwargs["MessageAttributes"]["AWS.SNS.SMS.SenderID"]["StringValue"] == "Fixture"


def test_environment_fields_preserve_long_compound_names(monkeypatch):
    monkeypatch.setenv("REVIEW_STORAGE_PROVIDER", "gcs")
    monkeypatch.setenv("REVIEW_STORAGE_BUCKET_NAME", "fixture-bucket")
    monkeypatch.setenv("REVIEW_COMMUNICATIONS_SMS_PROVIDER", "sns")
    monkeypatch.setenv("REVIEW_COMMUNICATIONS_SMS_SNS_AWS_SECRET_ACCESS_KEY", "fixture-private-value")
    settings = SwapLayerSettings.from_env(prefix="REVIEW_")
    assert settings.storage.bucket_name == "fixture-bucket"
    assert settings.communications.sms.sns.aws_secret_access_key == "fixture-private-value"


def test_explicit_stripe_and_twilio_providers_work_without_django():
    pytest.importorskip("stripe")
    pytest.importorskip("twilio")
    code = '''
import importlib.abc, sys
class NoDjango(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "django" or fullname.startswith("django."):
            raise ModuleNotFoundError("Django intentionally unavailable")
sys.meta_path.insert(0, NoDjango())
from swap_layer import configure, get_provider
configure(billing={"provider":"stripe","stripe":{"secret_key":"sk_test_fixture"}}, communications={"sms":{"provider":"twilio","twilio":{"account_sid":"ACfixture","auth_token":"fixture-token","from_number":"+15555551234"}}}, verification={"stripe_secret_key":"sk_test_fixture"})
assert get_provider("payments").get_vendor_client() is not None
assert get_provider("sms").client is not None
assert get_provider("verification").get_vendor_client() is not None
'''
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, encoding="utf-8", timeout=40)
    assert result.returncode == 0, result.stderr
