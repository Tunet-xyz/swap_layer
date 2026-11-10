"""Configuration errors describe a rejected value without repeating any part of it."""

import pytest

from swap_layer.exceptions import StripeKeyError, TwilioConfigError
from swap_layer.settings import SwapLayerSettings

SECRET = "Zq9Xw8Vv7Uu6Tt5Ss4Rr3Qq2"


def assert_not_repeated(message: str, secret: str = SECRET) -> None:
    for start in range(len(secret) - 3):
        assert secret[start : start + 4] not in message


@pytest.mark.parametrize(
    ("value", "description"),
    [
        (f"rk_live_{SECRET}", "a restricted key ('rk_...'"),
        (f"pk_live_{SECRET}", "a publishable key ('pk_...'"),
        (f"whsec_{SECRET}", "a webhook signing secret ('whsec_...'"),
        (SECRET, f"{len(SECRET)} characters and no recognised prefix"),
        ("", "The value is empty."),
    ],
)
def test_stripe_key_error_repeats_no_part_of_the_value(value, description):
    with pytest.raises(StripeKeyError) as exc_info:
        SwapLayerSettings(billing={"provider": "stripe", "stripe": {"secret_key": value}})
    message = str(exc_info.value)
    assert description in message
    assert_not_repeated(message)


@pytest.mark.parametrize(
    ("value", "description"),
    [
        (f"SK{SECRET}", "an API key SID ('SK...'"),
        (f"MG{SECRET}", "a Messaging Service SID ('MG...'"),
        (SECRET, f"{len(SECRET)} characters and no recognised prefix"),
    ],
)
def test_twilio_sid_error_repeats_no_part_of_the_value(value, description):
    with pytest.raises(TwilioConfigError) as exc_info:
        SwapLayerSettings(
            communications={
                "sms": {
                    "provider": "twilio",
                    "twilio": {
                        "account_sid": value,
                        "auth_token": "test-token",
                        "from_number": "+15555550100",
                    },
                }
            }
        )
    message = str(exc_info.value)
    assert description in message
    assert_not_repeated(message)


def test_phone_number_error_repeats_no_digits():
    error = TwilioConfigError.invalid_phone_number("0207 946 0958")
    message = str(error)
    assert "13 characters (starts with '+': False)" in message
    assert_not_repeated(message, "0207 946 0958")
