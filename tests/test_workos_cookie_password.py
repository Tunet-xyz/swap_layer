"""WorkOS cookie passwords are checked the same way whichever setting supplies them."""

import base64
from unittest.mock import patch

import pytest
from django.conf import settings

from swap_layer.exceptions import WorkOSConfigError
from swap_layer.settings import SwapLayerSettings, WorkOSAppConfig

pytest.importorskip("workos")

from swap_layer.identity.platform.providers.workos.client import WorkOSClient  # noqa: E402

VALID_KEY = base64.urlsafe_b64encode(bytes(range(32))).decode()
INVALID = [
    "short123",
    "x" * 32,  # long enough, but not a Fernet key
    "test_cookie_password_32_chars_min",
    base64.urlsafe_b64encode(bytes(32)).decode().rstrip("="),  # unpadded
    base64.urlsafe_b64encode(bytes(31)).decode(),  # 31 bytes
    "é" * 44,
]


def workos_apps(cookie_password: str) -> dict:
    return {"app": {"api_key": "sk_test", "client_id": "client_test", "cookie_password": cookie_password}}


@pytest.mark.parametrize("cookie_password", INVALID)
def test_structured_settings_reject_non_fernet_cookie_passwords(cookie_password):
    with pytest.raises(WorkOSConfigError, match="Fernet key"):
        SwapLayerSettings(identity={"provider": "workos", "workos_apps": workos_apps(cookie_password)})


@pytest.mark.parametrize("cookie_password", INVALID)
def test_django_workos_apps_reject_non_fernet_cookie_passwords(cookie_password):
    with patch.object(settings, "WORKOS_APPS", workos_apps(cookie_password)):
        with patch("swap_layer.identity.platform.providers.workos.client.WorkOSSDKClient") as sdk:
            with pytest.raises(WorkOSConfigError, match="Fernet key"):
                WorkOSClient(app_name="app")
    sdk.assert_not_called()


def test_valid_key_seals_and_unseals_with_the_workos_sdk():
    from workos.session import seal_data, unseal_data

    assert WorkOSAppConfig(**workos_apps(VALID_KEY)["app"]).cookie_password == VALID_KEY
    with patch.object(settings, "WORKOS_APPS", workos_apps(VALID_KEY)):
        with patch("swap_layer.identity.platform.providers.workos.client.WorkOSSDKClient"):
            client = WorkOSClient(app_name="app")
    assert unseal_data(seal_data({"user": "u-1"}, client._cookie_password), VALID_KEY) == {"user": "u-1"}


def test_former_error_name_still_builds_the_error():
    error = WorkOSConfigError.short_cookie_password(8)
    assert "Fernet key" in str(error)
    assert "8 characters" in str(error)
