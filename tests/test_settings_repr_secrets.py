"""Settings models keep credentials out of repr() and str()."""

import base64
import re

import pytest

from swap_layer import settings as settings_module
from swap_layer.settings import (
    Auth0AppConfig,
    BillingConfig,
    IdentityVerificationConfig,
    PayPalConfig,
    SNSConfig,
    SquareConfig,
    StripeConfig,
    TwilioConfig,
    WorkOSAppConfig,
    _ConfigModel,
)

CREDENTIAL_NAME = re.compile(r"secret|password|token|api_key|signature_key")
FERNET_KEY = base64.urlsafe_b64encode(b"k" * 32).decode("ascii")


def config_models():
    return sorted(
        (
            value
            for value in vars(settings_module).values()
            if isinstance(value, type) and issubclass(value, _ConfigModel) and value is not _ConfigModel
        ),
        key=lambda model: model.__name__,
    )


@pytest.mark.parametrize("model", config_models(), ids=lambda model: model.__name__)
def test_credential_fields_are_left_out_of_repr(model):
    exposed = [
        name
        for name, field in model.model_fields.items()
        if CREDENTIAL_NAME.search(name) and field.repr is not False
    ]
    assert exposed == []


def test_repr_and_str_never_show_credential_values():
    billing = BillingConfig(
        provider="stripe",
        stripe=StripeConfig(
            secret_key="sk_test_CREDENTIAL1",
            publishable_key="pk_test_visible",
            webhook_secret="whsec_CREDENTIAL2",
        ),
    )
    configs = [
        billing,
        PayPalConfig(client_id="paypal-client", client_secret="CREDENTIAL3"),
        SquareConfig(access_token="CREDENTIAL4", location_id="LOC-1", webhook_signature_key="CREDENTIAL5"),
        TwilioConfig(account_sid="AC123", auth_token="CREDENTIAL6", from_number="+15550100"),
        SNSConfig(aws_access_key_id="AKIA-visible", aws_secret_access_key="CREDENTIAL7"),
        WorkOSAppConfig(api_key="sk_CREDENTIAL8", client_id="client_visible", cookie_password=FERNET_KEY),
        Auth0AppConfig(
            client_id="auth0-client",
            client_secret="CREDENTIAL9",
            management_client_secret="CREDENTIAL10",
        ),
        IdentityVerificationConfig(
            stripe_secret_key="sk_test_CREDENTIAL11",
            stripe_webhook_secret="whsec_CREDENTIAL12",
        ),
    ]

    for config in configs:
        for text in (repr(config), str(config)):
            assert "CREDENTIAL" not in text
            assert FERNET_KEY not in text

    # Identifiers stay visible, and the values themselves are unchanged.
    assert "pk_test_visible" in repr(billing)
    assert "AKIA-visible" in repr(configs[4])
    assert billing.stripe is not None
    assert billing.stripe.secret_key == "sk_test_CREDENTIAL1"
    assert billing.model_dump()["stripe"]["webhook_secret"] == "whsec_CREDENTIAL2"
