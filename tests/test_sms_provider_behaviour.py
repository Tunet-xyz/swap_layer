"""SMS providers report what they actually do and use their own configuration."""

from unittest.mock import patch

import pytest


def test_twilio_opt_out_and_in_report_not_supported_without_api_calls():
    pytest.importorskip("twilio")
    from swap_layer.communications.sms.providers.twilio_sms import TwilioSMSProvider

    provider = TwilioSMSProvider(account_sid="ACtest", auth_token="test", from_number="+15555550100")
    with patch.object(provider, "client") as client:
        out = provider.opt_out_number("+15555550101")
        back = provider.opt_in_number("+15555550101")
    assert out["status"] == back["status"] == "not_supported"
    assert "STOP" in out["note"]
    assert out["phone_number"] == "+15555550101"
    assert client.mock_calls == []


def test_sns_phone_validation_uses_the_provider_account_and_region():
    pytest.importorskip("boto3")
    from swap_layer.communications.sms.providers.sns import SNSSMSProvider

    with patch("boto3.client") as client:
        provider = SNSSMSProvider(
            aws_access_key_id="AKIDEXAMPLE", aws_secret_access_key="example", region_name="eu-west-2"
        )
        client.return_value.phone_number_validate.return_value = {
            "NumberValidateResponse": {
                "CleansedPhoneNumberE164": "+447700900123",
                "CountryCodeIso2": "GB",
                "Carrier": "Example",
                "PhoneType": "MOBILE",
            }
        }
        with patch("django.conf.settings") as django_settings:
            provider.validate_phone_number("+447700900123")
    services = [call.args[0] for call in client.call_args_list]
    assert services == ["sns", "pinpoint"]
    sns_kwargs, pinpoint_kwargs = (call.kwargs for call in client.call_args_list)
    assert pinpoint_kwargs == sns_kwargs == {
        "aws_access_key_id": "AKIDEXAMPLE",
        "aws_secret_access_key": "example",
        "region_name": "eu-west-2",
    }
    assert django_settings.mock_calls == []
