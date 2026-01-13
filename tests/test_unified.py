import unittest
from unittest.mock import patch

from django.conf import settings

from swap_layer import get_provider


class TestUnifiedProvider(unittest.TestCase):
    """Test the unified get_provider() function."""

    def test_get_email_provider(self):
        """Test getting email provider through unified interface."""
        with patch.object(settings, "EMAIL_PROVIDER", "django"):
            provider = get_provider("email")
            from swap_layer.communications.email.adapter import EmailProviderAdapter

            self.assertIsInstance(provider, EmailProviderAdapter)

    def test_get_payment_provider(self):
        """Test getting payment provider through unified interface."""
        with patch.object(settings, "PAYMENT_PROVIDER", "stripe"):
            provider = get_provider("payment")
            from swap_layer.billing.adapter import PaymentProviderAdapter

            self.assertIsInstance(provider, PaymentProviderAdapter)

    def test_get_payments_provider_alias(self):
        """Test that 'billing' and 'payments' work as aliases."""
        with patch.object(settings, "PAYMENT_PROVIDER", "stripe"):
            provider = get_provider("billing")
            from swap_layer.billing.adapter import PaymentProviderAdapter

            self.assertIsInstance(provider, PaymentProviderAdapter)

    def test_get_sms_provider(self):
        """Test getting SMS provider through unified interface."""
        with patch.object(settings, "SMS_PROVIDER", "twilio"):
            with patch("twilio.rest.Client"):
                provider = get_provider("sms")
                from swap_layer.communications.sms.adapter import SMSProviderAdapter

                self.assertIsInstance(provider, SMSProviderAdapter)

    def test_get_storage_provider(self):
        """Test getting storage provider through unified interface."""
        with patch.object(settings, "STORAGE_PROVIDER", "local"):
            provider = get_provider("storage")
            from swap_layer.storage.adapter import StorageProviderAdapter

            self.assertIsInstance(provider, StorageProviderAdapter)

    def test_get_identity_provider(self):
        """Test getting identity provider through unified interface."""
        with patch.object(settings, "IDENTITY_PROVIDER", "workos"):
            with patch("swap_layer.identity.platform.providers.workos.client.WorkOSSDKClient"):
                provider = get_provider("identity")
                from swap_layer.identity.platform.adapter import AuthProviderAdapter

                self.assertIsInstance(provider, AuthProviderAdapter)

    def test_get_identity_with_app_name(self):
        """Test getting identity provider with app_name parameter."""
        with patch.object(settings, "IDENTITY_PROVIDER", "workos"):
            # Mock WORKOS_APPS to include the custom app
            mock_workos_apps = {
                "default": {
                    "api_key": "test_api_key",
                    "client_id": "test_client_id",
                    "cookie_password": "test_cookie_password_min_32_chars",
                },
                "custom": {
                    "api_key": "custom_api_key",
                    "client_id": "custom_client_id",
                    "cookie_password": "custom_cookie_password_min_32_chars",
                },
            }
            with patch.object(settings, "WORKOS_APPS", mock_workos_apps):
                with patch("swap_layer.identity.platform.providers.workos.client.WorkOSSDKClient"):
                    provider = get_provider("identity", app_name="custom")
                from swap_layer.identity.platform.adapter import AuthProviderAdapter

                self.assertIsInstance(provider, AuthProviderAdapter)

    def test_unknown_service_type_raises_error(self):
        """Test that unknown service type raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            get_provider("unknown_service")

        self.assertIn("Unknown service type", str(cm.exception))

    def test_case_insensitive_service_type(self):
        """Test that service type is case-insensitive."""
        with patch.object(settings, "EMAIL_PROVIDER", "django"):
            provider1 = get_provider("EMAIL")
            provider2 = get_provider("Email")
            provider3 = get_provider("email")

            from swap_layer.communications.email.adapter import EmailProviderAdapter

            self.assertIsInstance(provider1, EmailProviderAdapter)
            self.assertIsInstance(provider2, EmailProviderAdapter)
            self.assertIsInstance(provider3, EmailProviderAdapter)


if __name__ == "__main__":
    unittest.main()
