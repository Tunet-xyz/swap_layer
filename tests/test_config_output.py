"""Configuration output from the MCP config tool and swaplayer_check shows no credentials."""

import json
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command

from swap_layer._redaction import PUBLIC_CONFIG_FIELDS, redact_config
from swap_layer.management.commands.swaplayer_check import SECRET_MASK, Command
from swap_layer.mcp.server import _get_config
from swap_layer.settings import SwapLayerSettings

# Every credential below contains "private"; no output may contain it, in part or whole.
COOKIE = "private-cookie-password-" + "x" * 16


def full_settings() -> SwapLayerSettings:
    return SwapLayerSettings(
        billing={
            "provider": "square",
            "stripe": {
                "secret_key": "sk_private-stripe-secret",
                "publishable_key": "pk_public-stripe",
                "webhook_secret": "whsec_private-webhook",
            },
            "paypal": {"client_id": "public-paypal-client", "client_secret": "private-paypal"},
            "square": {
                "access_token": "private-square-token",
                "location_id": "public-location",
                "webhook_signature_key": "private-square-signature-key",
                "webhook_notification_url": "https://public.example/hook",
            },
        },
        communications={
            "email": {"provider": "smtp"},
            "sms": {
                "provider": "sns",
                "twilio": {
                    "account_sid": "ACprivate-twilio-sid",
                    "auth_token": "private-twilio-token",
                    "from_number": "+15555550100",
                },
                "sns": {
                    "aws_access_key_id": "AKIAPRIVATEKEYID",
                    "aws_secret_access_key": "private-aws-secret",
                    "region_name": "eu-west-1",
                },
            },
        },
        storage={
            "provider": "gcs",
            "bucket_name": "public-bucket",
            "credentials_path": "/private/credentials.json",
        },
        identity={
            "provider": "auth0",
            "workos_apps": {
                "default": {
                    "api_key": "private-workos-key",
                    "client_id": "public-workos-client",
                    "cookie_password": COOKIE,
                }
            },
            "auth0_apps": {
                "default": {"client_id": "public-auth0-client", "client_secret": "private-auth0"}
            },
            "auth0_domain": "public.auth0.example",
        },
        verification={"provider": "stripe", "stripe_secret_key": "sk_private-verification"},
    )


def assert_no_credentials(text: str) -> None:
    assert "private" not in text.lower()
    for fragment in ("AKIA", "whsec_", "sk_"):
        assert fragment not in text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "service", ["all", "payments", "email", "sms", "storage", "identity", "verification"]
)
async def test_mcp_config_shows_only_public_fields(service):
    with patch("swap_layer.settings.get_swaplayer_settings", return_value=full_settings()):
        result = await _get_config(service)
    assert result["status"] == "success"
    assert_no_credentials(json.dumps(result))


@pytest.mark.asyncio
async def test_mcp_config_keeps_public_identifiers():
    with patch("swap_layer.settings.get_swaplayer_settings", return_value=full_settings()):
        text = json.dumps(await _get_config("all"))
    for public in (
        "pk_public-stripe",
        "public-location",
        "https://public.example/hook",
        "public-workos-client",
        "public-auth0-client",
        "public.auth0.example",
        "eu-west-1",
        "public-bucket",
        "+15555550100",
    ):
        assert public in text


def test_redaction_is_an_allow_list():
    data = {
        "provider": "stripe",
        "api_keys": ["private-1", "private-2"],
        "nested": [{"unknown_field": "private-3", "region_name": "eu"}],
        "webhook_secret": None,
    }
    assert redact_config(data) == {
        "provider": "stripe",
        "api_keys": [],
        "nested": [{"region_name": "eu"}],
        "webhook_secret": None,
    }
    assert redact_config(data, mask="***")["api_keys"] == ["***", "***"]
    assert redact_config("private-scalar") is None
    assert "secret_key" not in PUBLIC_CONFIG_FIELDS


def run_check(*args: str, settings: SwapLayerSettings | None = None) -> str:
    settings = settings or full_settings()
    result = {"valid": True, "modules": settings.get_status(), "settings": settings}
    out = StringIO()
    with patch(
        "swap_layer.management.commands.swaplayer_check.validate_swaplayer_config",
        return_value=result,
    ):
        call_command(Command(), *args, stdout=out)
    return out.getvalue()


def test_check_verbose_masks_every_credential():
    output = run_check("--verbose")
    assert_no_credentials(output)
    assert f"cookie_password: {SECRET_MASK}" in output
    assert f"client_secret: {SECRET_MASK}" in output
    assert f"webhook_signature_key: {SECRET_MASK}" in output
    assert f"aws_access_key_id: {SECRET_MASK}" in output
    assert "public-workos-client" in output
    assert "public-location" in output


def test_check_verbose_for_one_module():
    output = run_check("--verbose", "--module", "identity")
    assert_no_credentials(output)
    assert "public-auth0-client" in output
    assert "public-location" not in output
