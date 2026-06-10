import unittest
from unittest.mock import MagicMock, patch

from django.conf import settings

from swap_layer.billing.adapter import PaymentProviderAdapter
from swap_layer.billing.factory import get_payment_provider
from swap_layer.billing.providers.stripe import StripePaymentProvider


class TestPaymentFactory(unittest.TestCase):
    def test_get_payment_provider_returns_stripe(self):
        """Test that the factory returns the correct provider based on settings."""
        with patch.object(settings, "PAYMENT_PROVIDER", "stripe"):
            provider = get_payment_provider()
            self.assertIsInstance(provider, StripePaymentProvider)
            self.assertIsInstance(provider, PaymentProviderAdapter)


class TestStripeProvider(unittest.TestCase):
    def setUp(self):
        self.provider = StripePaymentProvider(secret_key="sk_test_123")
        self.client = MagicMock()
        self.provider._client = self.client

    def test_create_customer_success(self):
        """Test successful customer creation."""
        mock_customer = MagicMock()
        mock_customer.id = "cus_123"
        mock_customer.email = "test@example.com"
        mock_customer.name = "Test User"
        mock_customer.created = 1234567890
        mock_customer.metadata = {}
        self.client.v1.customers.create.return_value = mock_customer

        result = self.provider.create_customer(email="test@example.com", name="Test User")

        self.assertEqual(result["id"], "cus_123")
        self.assertEqual(result["email"], "test@example.com")
        self.client.v1.customers.create.assert_called_once_with(
            params={"email": "test@example.com", "name": "Test User"}
        )

    def test_create_customer_error_handling(self):
        """Test that Stripe errors are converted to PaymentErrors."""
        import stripe

        error = stripe.CardError(
            message="Your card was declined.", param="card_number", code="card_declined"
        )
        self.client.v1.customers.create.side_effect = error

        from swap_layer.billing.adapter import PaymentDeclinedError

        with self.assertRaises(PaymentDeclinedError):
            self.provider.create_customer(email="fail@example.com")

    def test_escape_hatch(self):
        """Test that the escape hatch returns the configured StripeClient."""
        self.assertIs(self.provider.get_vendor_client(), self.client)


if __name__ == "__main__":
    unittest.main()
