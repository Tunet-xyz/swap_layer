"""Email and SMS provider requests wait a bounded time."""

import warnings
from unittest.mock import Mock, patch

import django.core.mail
import pytest
from django.test import override_settings

from swap_layer.communications.email._connection import default_email_connection
from swap_layer.communications.email.providers.django_email import DjangoEmailAdapter
from swap_layer.communications.email.providers.smtp import SMTPEmailProvider
from swap_layer.http import DEFAULT_TIMEOUT

SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


def connection_quietly():
    # Django 6.1 deprecates the EMAIL_* settings these tests configure.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return default_email_connection()


def test_smtp_backend_without_timeout_gets_default():
    with override_settings(EMAIL_BACKEND=SMTP_BACKEND, EMAIL_TIMEOUT=None):
        assert connection_quietly().timeout == DEFAULT_TIMEOUT


def test_configured_smtp_timeout_is_kept():
    with override_settings(EMAIL_BACKEND=SMTP_BACKEND, EMAIL_TIMEOUT=5):
        assert connection_quietly().timeout == 5


@pytest.mark.skipif(not hasattr(django.core.mail, "mailers"), reason="MAILERS needs Django 6.1+")
def test_smtp_mailer_without_timeout_gets_default():
    mailers = {"default": {"BACKEND": SMTP_BACKEND, "OPTIONS": {"host": "localhost"}}}
    with override_settings(MAILERS=mailers):
        assert connection_quietly().timeout == DEFAULT_TIMEOUT
    mailers["default"]["OPTIONS"]["timeout"] = 7
    with override_settings(MAILERS=mailers):
        assert connection_quietly().timeout == 7


def test_backends_without_timeouts_are_unchanged():
    connection = connection_quietly()  # tests use the locmem backend
    assert not hasattr(connection, "timeout")


def test_smtp_provider_sends_through_bounded_connection():
    connection = Mock()
    connection.send_messages.return_value = 1
    with patch(
        "swap_layer.communications.email.providers.smtp.default_email_connection",
        return_value=connection,
    ) as factory:
        result = SMTPEmailProvider().send_email(
            to=["user@example.com"], subject="Subject", text_body="Body"
        )
    assert result["status"] == "sent"
    factory.assert_called_once_with()
    (messages,) = connection.send_messages.call_args.args
    assert [message.to for message in messages] == [["user@example.com"]]


def test_smtp_bulk_send_reuses_the_open_connection():
    connection = Mock()
    connection.send_messages.return_value = 1
    with patch(
        "swap_layer.communications.email.providers.smtp.default_email_connection",
        return_value=connection,
    ) as factory:
        result = SMTPEmailProvider().send_bulk_email(
            recipients=[{"to": "a@example.com"}, {"to": "b@example.com"}],
            subject="Hello",
            text_body="Body",
        )
    assert result["total_sent"] == 2
    factory.assert_called_once_with()
    connection.open.assert_called_once_with()
    connection.close.assert_called_once_with()
    assert connection.send_messages.call_count == 2


def test_django_adapter_sends_through_bounded_connection():
    connection = Mock()
    with patch(
        "swap_layer.communications.email.providers.django_email.default_email_connection",
        return_value=connection,
    ):
        DjangoEmailAdapter().send_email(to=["user@example.com"], subject="Subject", text_body="Body")
    connection.send_messages.assert_called_once()


def test_django_adapter_still_delivers_to_configured_backend():
    django.core.mail.outbox = []
    DjangoEmailAdapter().send_email(to=["user@example.com"], subject="Subject", text_body="Body")
    assert [message.subject for message in django.core.mail.outbox] == ["Subject"]


def test_twilio_requests_have_a_timeout():
    pytest.importorskip("twilio")
    from swap_layer.communications.sms.providers.twilio_sms import TwilioSMSProvider

    provider = TwilioSMSProvider(account_sid="ACtest", auth_token="test", from_number="+15555550100")
    assert provider.client.http_client.timeout == DEFAULT_TIMEOUT
    custom = TwilioSMSProvider(
        account_sid="ACtest", auth_token="test", from_number="+15555550100", timeout=5
    )
    assert custom.client.http_client.timeout == 5
