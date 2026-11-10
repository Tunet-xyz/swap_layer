import unittest
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings

from swap_layer.communications.email.adapter import EmailProviderAdapter
from swap_layer.communications.email.factory import get_email_provider
from swap_layer.communications.email.providers.django_email import DjangoEmailAdapter


class TestEmailFactory(unittest.TestCase):
    @patch.object(settings, "EMAIL_PROVIDER", "django")
    def test_get_email_provider_returns_django_adapter(self):
        """Test that the factory returns the DjangoEmailAdapter."""
        provider = get_email_provider()
        self.assertIsInstance(provider, DjangoEmailAdapter)
        self.assertIsInstance(provider, EmailProviderAdapter)


class TestDjangoEmailProvider(unittest.TestCase):
    def setUp(self):
        self.provider = DjangoEmailAdapter()

    @patch("swap_layer.communications.email.providers.django_email.default_email_connection")
    @patch("swap_layer.communications.email.providers.django_email.EmailMultiAlternatives")
    def test_send_email_success(self, mock_email_class, mock_connection_factory):
        """Test successful email sending."""
        mock_msg = MagicMock()
        mock_email_class.return_value = mock_msg

        result = self.provider.send_email(
            to=["user@example.com"], subject="Hello", text_body="World"
        )

        self.assertEqual(result["status"], "sent")
        mock_connection_factory.return_value.send_messages.assert_called_once_with([mock_msg])
        mock_email_class.assert_called_with(
            subject="Hello",
            body="World",
            from_email=None,
            to=["user@example.com"],
            cc=None,
            bcc=None,
            reply_to=None,
            headers=None,
        )



def test_metadata_is_not_sent_as_message_headers():
    import django.core.mail

    django.core.mail.outbox = []
    DjangoEmailAdapter().send_email(
        to=["user@example.com"],
        subject="Hello",
        text_body="World",
        headers={"X-Campaign": "welcome"},
        metadata={"user_id": "u-123", "tags": ["onboarding"]},
    )
    (message,) = django.core.mail.outbox
    assert message.extra_headers == {"X-Campaign": "welcome"}
    assert "u-123" not in message.message().as_string()
    assert message.metadata == {"user_id": "u-123"}
    assert message.tags == ["onboarding"]



def test_string_tags_stay_one_tag_and_anymail_status_is_read():
    pytest.importorskip("anymail")
    import django.core.mail
    from django.test import override_settings

    with override_settings(EMAIL_BACKEND="anymail.backends.test.EmailBackend", ANYMAIL={}):
        django.core.mail.outbox = []
        result = DjangoEmailAdapter().send_email(
            to=["user@example.com"], subject="Hello", text_body="World",
            metadata={"tags": "welcome", "user_id": "u-1"},
        )
    (message,) = django.core.mail.outbox
    assert message.tags == ["welcome"]
    assert result["status"] == "sent"
    assert result["message_id"] == message.anymail_status.message_id


if __name__ == "__main__":
    unittest.main()
