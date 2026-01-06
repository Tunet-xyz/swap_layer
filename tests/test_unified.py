import unittest
from unittest.mock import MagicMock, patch
from swap_layer.config import settings
from swap_layer import get_provider


class TestUnifiedProvider(unittest.TestCase):
    """Test the unified get_provider() function."""

    def test_get_email_provider(self):
        """Test getting email provider through unified interface."""
        with patch.object(settings, 'get', return_value='django'):
            provider = get_provider('email')
            from swap_layer.email.adapter import EmailProviderAdapter
            self.assertIsInstance(provider, EmailProviderAdapter)

    def test_get_payment_provider(self):
        """Test getting payment provider through unified interface."""
        def mock_get(key, default=None):
            if key == 'PAYMENT_PROVIDER': return 'stripe'
            if key == 'STRIPE_SECRET_KEY': return 'sk_test_mock'
            return default
            
        with patch.object(settings, 'get', side_effect=mock_get):
            provider = get_provider('payment')
            from swap_layer.payments.adapter import PaymentProviderAdapter
            self.assertIsInstance(provider, PaymentProviderAdapter)

    def test_get_payments_provider_alias(self):
        """Test that 'payments' also works as alias."""
        def mock_get(key, default=None):
            if key == 'PAYMENT_PROVIDER': return 'stripe'
            if key == 'STRIPE_SECRET_KEY': return 'sk_test_mock'
            return default
            
        with patch.object(settings, 'get', side_effect=mock_get):
            provider = get_provider('payments')
            from swap_layer.payments.adapter import PaymentProviderAdapter
            self.assertIsInstance(provider, PaymentProviderAdapter)

    def test_get_sms_provider(self):
        """Test getting SMS provider through unified interface."""
        def mock_get(key, default=None):
            config = {
                'SMS_PROVIDER': 'twilio',
                'TWILIO_ACCOUNT_SID': 'AC_test',
                'TWILIO_AUTH_TOKEN': 'token_test',
                'TWILIO_FROM_NUMBER': '+15555551234'
            }
            return config.get(key, default)
            
        with patch.object(settings, 'get', side_effect=mock_get):
            with patch('swap_layer.sms.providers.twilio_sms.Client'):
                provider = get_provider('sms')
                from swap_layer.sms.adapter import SMSProviderAdapter
                self.assertIsInstance(provider, SMSProviderAdapter)

    def test_get_storage_provider(self):
        """Test getting storage provider through unified interface."""
        def mock_get(key, default=None):
            config = {
                'STORAGE_PROVIDER': 'local',
                'MEDIA_ROOT': '/tmp/media',
                'MEDIA_URL': '/media/'
            }
            return config.get(key, default)
            
        with patch.object(settings, 'get', side_effect=mock_get):
            provider = get_provider('storage')
            from swap_layer.storage.adapter import StorageProviderAdapter
            self.assertIsInstance(provider, StorageProviderAdapter)

    def test_get_identity_provider(self):
        """Test getting identity provider through unified interface."""
        def mock_get(key, default=None):
            config = {
                'IDENTITY_PROVIDER': 'workos',
                'WORKOS_API_KEY': 'sk_test',
                'WORKOS_CLIENT_ID': 'client_test'
            }
            return config.get(key, default)
            
        with patch.object(settings, 'get', side_effect=mock_get):
            with patch('swap_layer.identity.platform.providers.workos.client.workos'):
                provider = get_provider('identity')
                from swap_layer.identity.platform.adapter import AuthProviderAdapter
                self.assertIsInstance(provider, AuthProviderAdapter)

    def test_get_identity_with_app_name(self):
        """Test getting identity provider with app_name parameter."""
        def mock_get(key, default=None):
            config = {
                'IDENTITY_PROVIDER': 'workos',
                'WORKOS_API_KEY': 'sk_test',
                'WORKOS_CLIENT_ID': 'client_test'
            }
            return config.get(key, default)
            
        with patch.object(settings, 'get', side_effect=mock_get):
            with patch('swap_layer.identity.platform.providers.workos.client.workos'):
                provider = get_provider('identity', app_name='custom')
                from swap_layer.identity.platform.adapter import AuthProviderAdapter
                self.assertIsInstance(provider, AuthProviderAdapter)

    def test_unknown_service_type_raises_error(self):
        """Test that unknown service type raises ValueError."""
        with self.assertRaises(ValueError) as cm:
            get_provider('unknown_service')
        
        self.assertIn('Unknown service type', str(cm.exception))

    def test_case_insensitive_service_type(self):
        """Test that service type is case-insensitive."""
        with patch.object(settings, 'get', return_value='django'):
            provider1 = get_provider('EMAIL')
            provider2 = get_provider('Email')
            provider3 = get_provider('email')
            
            from swap_layer.email.adapter import EmailProviderAdapter
            self.assertIsInstance(provider1, EmailProviderAdapter)
            self.assertIsInstance(provider2, EmailProviderAdapter)
            self.assertIsInstance(provider3, EmailProviderAdapter)


class TestConfigSettings(unittest.TestCase):
    """Test the configuration wrapper."""

    def test_config_prefers_django_settings(self):
        """Test that Django settings are preferred over env vars."""
        import os
        os.environ['TEST_KEY'] = 'env_value'
        
        with patch('django.conf.settings') as mock_django_settings:
            mock_django_settings.configured = True
            mock_django_settings.TEST_KEY = 'django_value'
            
            from swap_layer.config import Settings
            config = Settings()
            result = config.get('TEST_KEY')
            
            self.assertEqual(result, 'django_value')
        
        del os.environ['TEST_KEY']

    def test_config_falls_back_to_env(self):
        """Test that env vars are used when Django settings not available."""
        import os
        os.environ['TEST_KEY'] = 'env_value'
        
        # Django not configured
        with patch('swap_layer.config.settings.get') as mock_get:
            mock_get.side_effect = ImportError
            
            from swap_layer.config import Settings
            config = Settings()
            result = config.get('TEST_KEY')
            
            self.assertEqual(result, 'env_value')
        
        del os.environ['TEST_KEY']

    def test_config_returns_default(self):
        """Test that default value is returned when key not found."""
        from swap_layer.config import Settings
        config = Settings()
        result = config.get('NONEXISTENT_KEY', 'default_value')
        
        self.assertEqual(result, 'default_value')


if __name__ == '__main__':
    unittest.main()
