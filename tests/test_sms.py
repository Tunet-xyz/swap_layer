import unittest
from unittest.mock import MagicMock, patch

from django.conf import settings

from swap_layer.communications.sms.adapter import SMSProviderAdapter
from swap_layer.communications.sms.factory import get_sms_provider
from swap_layer.communications.sms.providers.twilio_sms import TwilioSMSProvider


class TestSMSFactory(unittest.TestCase):
    def test_get_sms_provider_returns_twilio(self):
        """Test that the factory returns the correct provider based on settings."""
        with patch.object(settings, "SMS_PROVIDER", "twilio"):
            provider = get_sms_provider()
            self.assertIsInstance(provider, TwilioSMSProvider)
            self.assertIsInstance(provider, SMSProviderAdapter)

    def test_factory_raises_for_unknown_provider(self):
        """Test that the factory raises ValueError for unknown providers."""
        from swap_layer.settings import SwapLayerSettings

        # Create mock settings with unknown provider
        mock_settings = SwapLayerSettings(
            communications={
                "sms": {
                    "provider": "twilio",
                    "twilio": {
                        "account_sid": "AC123",
                        "auth_token": "test",
                        "from_number": "+1555",
                    },
                }
            }
        )
        # Override provider to invalid value after creation
        mock_settings.communications.sms.provider = "unknown"

        with patch(
            "swap_layer.communications.sms.factory.get_swaplayer_settings",
            return_value=mock_settings,
        ):
            with self.assertRaises(ValueError):
                get_sms_provider()


class TestTwilioProvider(unittest.TestCase):
    def setUp(self):
        with patch("twilio.rest.Client") as mock_client_class:
            self.mock_client = MagicMock()
            mock_client_class.return_value = self.mock_client
            self.provider = TwilioSMSProvider()

    def test_send_sms_success(self):
        """Test successful SMS sending."""
        mock_message = MagicMock()
        mock_message.sid = "SM123456"
        mock_message.status = "queued"
        mock_message.to = "+15555555678"
        mock_message.from_ = "+15555551234"
        mock_message.num_segments = 1

        self.mock_client.messages.create.return_value = mock_message

        result = self.provider.send_sms(to="+15555555678", message="Test message")

        self.assertEqual(result["message_id"], "SM123456")
        self.assertEqual(result["status"], "queued")
        self.assertEqual(result["to"], "+15555555678")
        self.assertEqual(result["segments"], 1)
        self.mock_client.messages.create.assert_called_once()

    def test_send_sms_with_custom_from_number(self):
        """Test SMS sending with custom from number."""
        mock_message = MagicMock()
        mock_message.sid = "SM123456"
        mock_message.status = "sent"
        self.mock_client.messages.create.return_value = mock_message

        self.provider.send_sms(to="+15555555678", message="Test", from_number="+15555559999")

        call_args = self.mock_client.messages.create.call_args
        self.assertEqual(call_args.kwargs["from_"], "+15555559999")

    def test_send_bulk_sms_success(self):
        """Test successful bulk SMS sending."""
        mock_message = MagicMock()
        mock_message.sid = "SM123456"
        mock_message.status = "sent"
        self.mock_client.messages.create.return_value = mock_message

        recipients = [
            {"to": "+15555551111", "message": "Hello Alice"},
            {"to": "+15555552222", "message": "Hello Bob"},
            {"to": "+15555553333"},  # Will use default message
        ]

        result = self.provider.send_bulk_sms(recipients=recipients, message="Default message")

        self.assertEqual(result["total_sent"], 3)
        self.assertEqual(result["total_failed"], 0)
        self.assertEqual(self.mock_client.messages.create.call_count, 3)

    def test_send_bulk_sms_with_failures(self):
        """Test bulk SMS with some failures."""

        def mock_create(**kwargs):
            if kwargs["to"] == "+15555552222":
                from twilio.base.exceptions import TwilioRestException

                raise TwilioRestException(status=400, uri="", msg="Invalid phone number")
            mock_msg = MagicMock()
            mock_msg.sid = "SM123"
            mock_msg.status = "sent"
            return mock_msg

        self.mock_client.messages.create.side_effect = mock_create

        recipients = [
            {"to": "+15555551111"},
            {"to": "+15555552222"},  # Will fail
            {"to": "+15555553333"},
        ]

        result = self.provider.send_bulk_sms(recipients=recipients, message="Test")

        self.assertEqual(result["total_sent"], 2)
        self.assertEqual(result["total_failed"], 1)
        self.assertEqual(len(result["failed_recipients"]), 1)
        self.assertEqual(result["failed_recipients"][0]["to"], "+15555552222")

    def test_get_message_status(self):
        """Test retrieving message status."""
        mock_message = MagicMock()
        mock_message.sid = "SM123456"
        mock_message.status = "delivered"
        mock_message.error_code = None
        mock_message.error_message = None

        self.mock_client.messages.return_value.fetch.return_value = mock_message

        result = self.provider.get_message_status("SM123456")

        self.assertEqual(result["message_id"], "SM123456")
        self.assertEqual(result["status"], "delivered")
        self.assertIsNone(result["error"])

    def test_validate_phone_number(self):
        """Test phone number validation."""
        mock_lookup = MagicMock()
        mock_lookup.phone_number = "+15555555678"
        mock_lookup.country_code = "US"
        mock_lookup.carrier = {"name": "Verizon", "type": "mobile"}

        self.mock_client.lookups.v1.phone_numbers.return_value.fetch.return_value = mock_lookup

        result = self.provider.validate_phone_number("+15555555678")

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["phone_number"], "+15555555678")
        self.assertEqual(result["country_code"], "US")
        self.assertIsNone(result["carrier"])  # Requires carrier lookup add-on
        self.assertIsNone(result["line_type"])  # Requires carrier lookup add-on

    def test_get_account_balance(self):
        """Test retrieving account balance."""
        mock_balance = MagicMock()
        mock_balance.balance = "25.00"
        mock_balance.currency = "USD"

        self.mock_client.balance.fetch.return_value = mock_balance

        result = self.provider.get_account_balance()

        self.assertEqual(result["balance"], 25.0)  # Implementation converts to float
        self.assertEqual(result["currency"], "USD")

    def test_sms_send_error_handling(self):
        """Test that Twilio errors are converted to SMSSendError."""
        from twilio.base.exceptions import TwilioRestException

        from swap_layer.communications.sms.adapter import SMSSendError

        error = TwilioRestException(status=400, uri="", msg="Invalid phone number format")
        self.mock_client.messages.create.side_effect = error

        with self.assertRaises(SMSSendError):
            self.provider.send_sms(to="invalid", message="Test")


if __name__ == "__main__":
    unittest.main()
