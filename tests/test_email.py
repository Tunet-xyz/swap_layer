import unittest
from unittest.mock import MagicMock, patch

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


if __name__ == "__main__":
    unittest.main()
