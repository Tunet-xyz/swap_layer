"""Misspelt settings fail validation; every settings field can come from the environment."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from swap_layer.exceptions import ConfigurationError
from swap_layer.settings import SwapLayerSettings

KEY = "c3dhcC1sYXllci10ZXN0LWNvb2tpZS1rZXktMzJieSE="


@pytest.mark.parametrize(
    "config",
    [
        {"billing": {"provider": "stripe", "stripe": {"secret_key": "sk_test_1", "webhok_secret": "x"}}},
        {"billing": {"provider": "stripe", "provder": "x", "stripe": {"secret_key": "sk_test_1"}}},
        {"communications": {"sms": {"provider": "sns", "sns": {"region": "eu-west-1"}}}},
        {"communications": {"emial": {"provider": "django"}}},
        {"storage": {"provider": "local", "media_rot": "/tmp"}},
        {"identity": {"provider": "workos", "workos_apps": {"app": {
            "api_key": "k", "client_id": "c", "cookie_password": KEY, "redirect_url": "x"}}}},
        {"verification": {"provider": "stripe", "stripe_secret_key": "sk_test_1", "mode": "x"}},
    ],
)
def test_misspelt_nested_settings_are_rejected(config):
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        SwapLayerSettings(**config)


def test_legacy_app_dicts_may_carry_application_keys():
    django_settings = SimpleNamespace(
        IDENTITY_PROVIDER="workos",
        WORKOS_APPS={"app": {"api_key": "k", "client_id": "c", "cookie_password": KEY, "redirect_url": "/x"}},
    )
    settings = SwapLayerSettings._from_legacy_django_settings(django_settings)
    assert settings.identity.workos_apps["app"].client_id == "c"


@pytest.fixture
def clean_env(monkeypatch):
    import os

    for key in list(os.environ):
        if key.startswith("SWAPLAYER_"):
            monkeypatch.delenv(key)
    return monkeypatch


def test_environment_reaches_every_settings_area(clean_env):
    env = {
        "SWAPLAYER_DEBUG": "true",
        "SWAPLAYER_RAISE_ON_ERROR": "false",
        "SWAPLAYER_BILLING_PROVIDER": "stripe",
        "SWAPLAYER_BILLING_STRIPE_SECRET_KEY": "sk_test_env",
        "SWAPLAYER_COMMUNICATIONS_EMAIL_PROVIDER": "smtp",
        "SWAPLAYER_COMMUNICATIONS_SMS_PROVIDER": "twilio",
        "SWAPLAYER_COMMUNICATIONS_SMS_TWILIO_ACCOUNT_SID": "ACenv",
        "SWAPLAYER_COMMUNICATIONS_SMS_TWILIO_AUTH_TOKEN": "token",
        "SWAPLAYER_COMMUNICATIONS_SMS_TWILIO_FROM_NUMBER": "+15555550100",
        "SWAPLAYER_STORAGE_PROVIDER": "local",
        "SWAPLAYER_STORAGE_MEDIA_ROOT": "./media",
        "SWAPLAYER_IDENTITY_PROVIDER": "auth0",
        "SWAPLAYER_IDENTITY_AUTH0_DOMAIN": "tenant.auth0.example",
        "SWAPLAYER_IDENTITY_AUTH0_APPS_CUSTOMER_PORTAL_CLIENT_ID": "portal-client",
        "SWAPLAYER_IDENTITY_AUTH0_APPS_CUSTOMER_PORTAL_CLIENT_SECRET": "portal-secret",
        "SWAPLAYER_IDENTITY_WORKOS_APPS_DEFAULT_API_KEY": "sk_workos",
        "SWAPLAYER_IDENTITY_WORKOS_APPS_DEFAULT_CLIENT_ID": "client_workos",
        "SWAPLAYER_IDENTITY_WORKOS_APPS_DEFAULT_COOKIE_PASSWORD": KEY,
        "SWAPLAYER_VERIFICATION_PROVIDER": "stripe",
        "SWAPLAYER_VERIFICATION_STRIPE_SECRET_KEY": "sk_test_identity",
    }
    for key, value in env.items():
        clean_env.setenv(key, value)

    settings = SwapLayerSettings.from_env()

    assert settings.debug is True
    assert settings.raise_on_error is False
    assert settings.billing.stripe.secret_key == "sk_test_env"
    assert settings.communications.email.provider == "smtp"
    assert settings.communications.sms.twilio.account_sid == "ACenv"
    assert settings.storage.media_root == "./media"
    assert settings.identity.auth0_domain == "tenant.auth0.example"
    assert settings.identity.auth0_apps["customer_portal"].client_secret == "portal-secret"
    assert settings.identity.workos_apps["default"].cookie_password == KEY
    assert settings.verification.stripe_secret_key == "sk_test_identity"


@pytest.mark.parametrize(
    "name",
    ["SWAPLAYER_BILLING_STRIPE_SECRETKEY", "SWAPLAYER_EMAIL_PROVIDER", "SWAPLAYER_SMS_PROVIDER"],
)
def test_misspelt_environment_variables_are_reported(clean_env, name):
    clean_env.setenv("SWAPLAYER_BILLING_PROVIDER", "stripe")
    clean_env.setenv("SWAPLAYER_BILLING_STRIPE_SECRET_KEY", "sk_test_env")
    clean_env.setenv(name, "x")
    with pytest.raises(ValidationError):
        SwapLayerSettings.from_env()


def test_conflicting_environment_variables_are_reported(clean_env):
    clean_env.setenv("SWAPLAYER_BILLING", "stripe")
    clean_env.setenv("SWAPLAYER_BILLING_PROVIDER", "stripe")
    with pytest.raises(ConfigurationError, match="SWAPLAYER_BILLING"):
        SwapLayerSettings.from_env()
