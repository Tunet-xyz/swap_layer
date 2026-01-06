import unittest
from unittest.mock import MagicMock, patch
from swap_layer.config import settings
from swap_layer.payments.factory import get_payment_provider
from swap_layer.payments.adapter import PaymentProviderAdapter, PaymentError
from swap_layer.payments.providers.stripe import StripePaymentProvider

class TestPaymentFactory(unittest.TestCase):
    def test_get_payment_provider_returns_stripe(self):
        """Test that the factory returns the correct provider based on settings."""
        # Config behavior: return configured defaults for known keys
        def mock_get(key, default=None):
            if key == 'PAYMENT_PROVIDER': return 'stripe'
            if key == 'STRIPE_SECRET_KEY': return 'sk_test_mock'
            return default
            
        with patch.object(settings, 'get', side_effect=mock_get):
            provider = get_payment_provider()
            self.assertIsInstance(provider, StripePaymentProvider)
            self.assertIsInstance(provider, PaymentProviderAdapter)

class TestStripeProvider(unittest.TestCase):
    def setUp(self):
        # Mock settings for initialization
        self.settings_patcher = patch.object(settings, 'get')
        self.mock_get = self.settings_patcher.start()
        self.mock_get.side_effect = lambda k, d=None: 'sk_test_mock' if k == 'STRIPE_SECRET_KEY' else d
        
        self.provider = StripePaymentProvider()

    def tearDown(self):
        self.settings_patcher.stop()

    @patch('swap_layer.payments.providers.stripe.stripe.Customer.create')
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

        self.assertEqual(result['id'], "cus_123")
        self.assertEqual(result['email'], "test@example.com")
        mock_create.assert_called_once()

    @patch('swap_layer.payments.providers.stripe.stripe.Customer.create')
    def test_create_customer_error_handling(self, mock_create):
        """Test that Stripe errors are converted to PaymentErrors."""
        # Simulate a Stripe CardError
        import stripe
        error = stripe.error.CardError(
            message="Your card was declined.",
            param="card_number",
            code="card_declined"
        )
        mock_create.side_effect = error

        # Verify that our custom exception is raised
        from swap_layer.payments.adapter import PaymentDeclinedError
        with self.assertRaises(PaymentDeclinedError):
            self.provider.create_customer(email="fail@example.com")

    def test_escape_hatch(self):
        """Test that the escape hatch returns the raw stripe module."""
        client = self.provider.get_vendor_client()
        import stripe
        self.assertEqual(client, stripe)

if __name__ == '__main__':
    unittest.main()
