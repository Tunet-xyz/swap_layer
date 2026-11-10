"""Identity clients read SWAPLAYER.identity, fall back to legacy settings, and keep OAuth state."""

from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest

from swap_layer.settings import SwapLayerSettings

pytest.importorskip("workos")
pytest.importorskip("authlib")

KEY = "c3dhcC1sYXllci10ZXN0LWNvb2tpZS1rZXktMzJieSE="
CONFIG = "swap_layer.identity.platform._config.get_swaplayer_settings"


def auth0_settings(**app_extra) -> SwapLayerSettings:
    return SwapLayerSettings(
        identity={
            "provider": "auth0",
            "auth0_apps": {
                "developer": {"client_id": "structured-client", "client_secret": "s", **app_extra}
            },
            "auth0_domain": "structured.auth0.example",
        }
    )


def test_management_factory_uses_the_structured_provider():
    # The Django test settings say IDENTITY_PROVIDER = "workos"; SWAPLAYER.identity wins.
    from swap_layer.identity.platform.management.factory import get_management_client
    from swap_layer.identity.platform.providers.auth0.management.client import (
        Auth0ManagementClient,
    )

    with patch(CONFIG, return_value=auth0_settings()):
        client = get_management_client()
    assert isinstance(client, Auth0ManagementClient)
    assert client.base_url == "https://structured.auth0.example/api/v2"
    assert client.client_id == "structured-client"


def test_auth0_management_credentials_can_be_separate():
    from swap_layer.identity.platform.providers.auth0.management.client import (
        Auth0ManagementClient,
    )

    settings = auth0_settings(management_client_id="m2m-client", management_client_secret="m2m")
    with patch(CONFIG, return_value=settings):
        client = Auth0ManagementClient("developer")
    assert (client.client_id, client.client_secret) == ("m2m-client", "m2m")


def test_workos_clients_use_structured_apps():
    from swap_layer.identity.platform.management.factory import get_management_client
    from swap_layer.identity.platform.providers.workos.client import WorkOSClient

    settings = SwapLayerSettings(
        identity={
            "provider": "workos",
            "workos_apps": {"portal": {"api_key": "sk_portal", "client_id": "c", "cookie_password": KEY}},
        }
    )
    with patch(CONFIG, return_value=settings):
        with patch("swap_layer.identity.platform.providers.workos.client.WorkOSSDKClient") as sdk:
            WorkOSClient(app_name="portal")
        management = get_management_client("portal")
    assert sdk.call_args.kwargs == {"api_key": "sk_portal", "client_id": "c"}
    assert management.api_key == "sk_portal"


def test_legacy_django_settings_remain_a_fallback():
    from swap_layer.identity.platform.providers.auth0.client import Auth0Client
    from swap_layer.identity.platform.providers.workos.client import WorkOSClient

    with patch(CONFIG, return_value=SwapLayerSettings()):
        with patch("swap_layer.identity.platform.providers.workos.client.WorkOSSDKClient"):
            workos = WorkOSClient(app_name="custom_app")  # tests/conftest.py WORKOS_APPS
        auth0 = Auth0Client(app_name="developer")  # tests/conftest.py AUTH0_APPS
    assert workos.app_name == "custom_app"
    assert auth0.domain == "test.auth0.com"
    assert auth0.get_logout_url(None, "https://app.example/").startswith("https://test.auth0.com/v2/logout?")


def test_missing_apps_and_domain_are_reported():
    from swap_layer.identity.platform._config import auth0_app_config, workos_app_config

    with patch(CONFIG, return_value=SwapLayerSettings()):
        with pytest.raises(ValueError, match="'missing' not found"):
            workos_app_config("missing")
        with pytest.raises(ValueError, match="'missing' not found"):
            auth0_app_config("missing")
    no_domain = SwapLayerSettings(
        identity={"provider": "auth0", "auth0_apps": {"x": {"client_id": "c", "client_secret": "s"}}, "auth0_domain": "d"}
    )
    no_domain.identity.auth0_domain = None
    with patch(CONFIG, return_value=no_domain), patch(
        "swap_layer.identity.platform._config._django_setting", return_value=""
    ):
        with pytest.raises(ValueError, match="domain"):
            auth0_app_config("x")


def test_auth0_callback_verifies_the_saved_state(monkeypatch):
    from authlib.integrations.base_client.errors import MismatchingStateError
    from authlib.integrations.django_client.apps import DjangoOAuth2App
    from django.test import RequestFactory

    from swap_layer.identity.platform.providers.auth0.client import Auth0Client

    metadata = {
        "issuer": "https://structured.auth0.example/",
        "authorization_endpoint": "https://structured.auth0.example/authorize",
        "token_endpoint": "https://structured.auth0.example/oauth/token",
        "jwks_uri": "https://structured.auth0.example/.well-known/jwks.json",
    }
    monkeypatch.setattr(DjangoOAuth2App, "load_server_metadata", lambda self: metadata)
    with patch(CONFIG, return_value=auth0_settings()):
        client = Auth0Client(app_name="developer")

    requests = RequestFactory()
    login = requests.get("/login")
    login.session = {}
    url = client.get_authorization_url(login, "https://app.example/callback")
    query = parse_qs(urlparse(url).query)
    state, nonce = query["state"][0], query["nonce"][0]

    callback = requests.get("/callback", {"code": "abc", "state": state})
    callback.session = login.session
    userinfo = {"sub": "auth0|1", "email": "user@example.com", "email_verified": True}
    with patch.object(
        DjangoOAuth2App, "fetch_access_token", return_value={"access_token": "t", "id_token": "i"}
    ) as fetch, patch.object(DjangoOAuth2App, "parse_id_token", return_value=userinfo) as parse:
        user = client.exchange_code_for_user(callback, "abc")
    assert user["id"] == "auth0|1"
    assert fetch.call_args.kwargs["redirect_uri"] == "https://app.example/callback"
    assert parse.call_args.kwargs["nonce"] == nonce

    replay = requests.get("/callback", {"code": "abc", "state": state})
    replay.session = login.session  # the state was consumed by the first callback
    with pytest.raises(MismatchingStateError):
        client.exchange_code_for_user(replay, "abc")


def test_auth0_token_cache_key_carries_the_library_prefix():
    from swap_layer.identity.platform.providers.auth0.management.client import (
        Auth0ManagementClient,
    )

    with patch(CONFIG, return_value=auth0_settings()):
        key = Auth0ManagementClient("developer")._token_cache_key
    assert key.startswith("swap_layer:auth0_mgmt_token:developer:")
    assert "structured-client" not in key  # the client ID is hashed, not stored
