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
        self.provider = StripePaymentProvider()

    @patch("swap_layer.billing.providers.stripe.stripe.Customer.create")
    def test_create_customer_success(self, mock_create):
        """Test successful customer creation."""
        # Mock the Stripe API response
        mock_customer = MagicMock()
        mock_customer.id = "cus_123"
        mock_customer.email = "test@example.com"
        mock_customer.name = "Test User"
        mock_customer.created = 1234567890
        mock_customer.metadata = {}
        mock_create.return_value = mock_customer

        result = self.provider.create_customer(email="test@example.com", name="Test User")

        self.assertEqual(result["id"], "cus_123")
        self.assertEqual(result["email"], "test@example.com")
        mock_create.assert_called_once()

    @patch("swap_layer.billing.providers.stripe.stripe.Customer.create")
    def test_create_customer_error_handling(self, mock_create):
        """Test that Stripe errors are converted to PaymentErrors."""
        # Simulate a Stripe CardError
        import stripe

        error = stripe.error.CardError(
            message="Your card was declined.", param="card_number", code="card_declined"
        )
        mock_create.side_effect = error

        # Verify that our custom exception is raised
        from swap_layer.billing.adapter import PaymentDeclinedError

        with self.assertRaises(PaymentDeclinedError):
            self.provider.create_customer(email="fail@example.com")

    def test_escape_hatch(self):
        """Test that the escape hatch returns the raw stripe module."""
        client = self.provider.get_vendor_client()
        import stripe

        self.assertEqual(client, stripe)


if __name__ == "__main__":
    unittest.main()
