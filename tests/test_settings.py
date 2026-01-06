"""
Tests for SwapLayer settings management system.
"""
import os
import pytest
from django.core.exceptions import ImproperlyConfigured
from pydantic import ValidationError

from swap_layer.settings import (
    SwapLayerSettings,
    PaymentsConfig,
    StripeConfig,
    SMSConfig,
    TwilioConfig,
    get_swaplayer_settings,
    validate_swaplayer_config,
)
from swap_layer.exceptions import (
    StripeKeyError,
    TwilioConfigError,
    WorkOSConfigError,
    ProviderConfigMismatchError,
    ModuleNotConfiguredError,
)


class TestStripeConfig:
    def test_valid_stripe_config(self):
        """Test valid Stripe configuration."""
        config = StripeConfig(
            secret_key='sk_test_123',
            publishable_key='pk_test_123',
        )
        assert config.secret_key == 'sk_test_123'
        assert config.publishable_key == 'pk_test_123'
    
    def test_stripe_secret_key_validation(self):
        """Test that secret key must start with sk_."""
        with pytest.raises(StripeKeyError):
            StripeConfig(secret_key='pk_test_123')


class TestTwilioConfig:
    def test_valid_twilio_config(self):
        """Test valid Twilio configuration."""
        config = TwilioConfig(
            account_sid='AC123',
            auth_token='test_token',
            from_number='+15555551234',
        )
        assert config.account_sid == 'AC123'
    
    def test_phone_number_validation(self):
        """Test that phone number must be E.164 format."""
        with pytest.raises(TwilioConfigError):
            TwilioConfig(
                account_sid='AC123',
                auth_token='token',
                from_number='5555551234',  # Missing +
            )
    
    def test_account_sid_validation(self):
        """Test that Account SID must start with AC."""
        with pytest.raises(TwilioConfigError):
            TwilioConfig(
                account_sid='XX123',
                auth_token='token',
                from_number='+15555551234',
            )


class TestPaymentsConfig:
    def test_stripe_config_required_when_provider_is_stripe(self):
        """Test that Stripe config is required when using Stripe provider."""
        with pytest.raises(ProviderConfigMismatchError):
            PaymentsConfig(provider='stripe')
    
    def test_valid_payments_config(self):
        """Test valid payments configuration."""
        config = PaymentsConfig(
            provider='stripe',
            stripe=StripeConfig(secret_key='sk_test_123')
        )
        assert config.provider == 'stripe'
        assert config.stripe.secret_key == 'sk_test_123'


class TestSMSConfig:
    def test_twilio_config_required_when_provider_is_twilio(self):
        """Test that Twilio config is required."""
        with pytest.raises(ProviderConfigMismatchError):
            SMSConfig(provider='twilio')
    
    def test_valid_sms_config(self):
        """Test valid SMS configuration."""
        config = SMSConfig(
            provider='twilio',
            twilio=TwilioConfig(
                account_sid='AC123',
                auth_token='token',
                from_number='+15555551234',
            )
        )
        assert config.provider == 'twilio'


class TestSwapLayerSettings:
    def test_minimal_config(self):
        """Test minimal configuration."""
        settings = SwapLayerSettings()
        assert settings.payments is None
        assert settings.debug is False
    
    def test_full_config(self):
        """Test full configuration."""
        settings = SwapLayerSettings(
            payments=PaymentsConfig(
                provider='stripe',
                stripe=StripeConfig(secret_key='sk_test_123')
            ),
            sms=SMSConfig(
                provider='twilio',
                twilio=TwilioConfig(
                    account_sid='AC123',
                    auth_token='token',
                    from_number='+15555551234',
                )
            ),
            debug=True,
        )
        assert settings.payments.provider == 'stripe'
        assert settings.sms.provider == 'twilio'
        assert settings.debug is True
    
    def test_from_dict(self):
        """Test creating settings from dictionary."""
        settings = SwapLayerSettings(
            payments={
                'provider': 'stripe',
                'stripe': {'secret_key': 'sk_test_123'}
            }
        )
        assert settings.payments.provider == 'stripe'
        assert settings.payments.stripe.secret_key == 'sk_test_123'
    
    def test_get_status(self):
        """Test getting configuration status."""
        settings = SwapLayerSettings(
            payments={
                'provider': 'stripe',
                'stripe': {'secret_key': 'sk_test_123'}
            }
        )
        status = settings.get_status()
        assert 'payments' in status
        assert status['payments'].startswith('configured')
        assert status['email'] == 'not configured'
    
    def test_validate_module(self):
        """Test module validation."""
        settings = SwapLayerSettings(
            payments={
                'provider': 'stripe',
                'stripe': {'secret_key': 'sk_test_123'}
            }
        )
        
        # Should not raise for configured module
        settings.validate_module('payments')
        
        # Should raise for unconfigured module
        with pytest.raises(ModuleNotConfiguredError):
            settings.validate_module('email')
    
    def test_repr(self):
        """Test string representation."""
        settings = SwapLayerSettings(
            payments={
                'provider': 'stripe',
                'stripe': {'secret_key': 'sk_test_123'}
            }
        )
        repr_str = repr(settings)
        assert 'SwapLayerSettings' in repr_str
        assert 'payments' in repr_str
    
    def test_extra_fields_forbidden(self):
        """Test that extra fields are not allowed (prevents typos)."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            SwapLayerSettings(
                payment={'provider': 'stripe'}  # Typo: should be 'payments'
            )


class TestEnvironmentVariables:
    @pytest.mark.xfail(reason="Environment variable nested dict parsing needs refinement")
    def test_from_env_payments(self, monkeypatch):
        """Test loading payments config from environment."""
        monkeypatch.setenv('SWAPLAYER_PAYMENTS_PROVIDER', 'stripe')
        monkeypatch.setenv('SWAPLAYER_PAYMENTS_STRIPE_SECRET_KEY', 'sk_test_123')
        
        settings = SwapLayerSettings.from_env()
        assert settings.payments.provider == 'stripe'
        assert settings.payments.stripe.secret_key == 'sk_test_123'
    
    @pytest.mark.xfail(reason="Environment variable nested dict parsing needs refinement")
    def test_from_env_sms(self, monkeypatch):
        """Test loading SMS config from environment."""
        monkeypatch.setenv('SWAPLAYER_SMS_PROVIDER', 'twilio')
        monkeypatch.setenv('SWAPLAYER_SMS_TWILIO_ACCOUNT_SID', 'AC123')
        monkeypatch.setenv('SWAPLAYER_SMS_TWILIO_AUTH_TOKEN', 'token')
        monkeypatch.setenv('SWAPLAYER_SMS_TWILIO_FROM_NUMBER', '+15555551234')
        
        settings = SwapLayerSettings.from_env()
        assert settings.sms.provider == 'twilio'
        assert settings.sms.twilio.account_sid == 'AC123'
    
    @pytest.mark.xfail(reason="Environment variable nested dict parsing needs refinement")
    def test_from_env_custom_prefix(self, monkeypatch):
        """Test loading with custom prefix."""
        monkeypatch.setenv('MYAPP_PAYMENTS_PROVIDER', 'stripe')
        monkeypatch.setenv('MYAPP_PAYMENTS_STRIPE_SECRET_KEY', 'sk_test_123')
        
        settings = SwapLayerSettings.from_env(prefix='MYAPP_')
        assert settings.payments.provider == 'stripe'


class TestLegacyCompatibility:
    @pytest.mark.xfail(reason="Needs proper Django settings mock setup")
    def test_from_legacy_django_settings(self, settings):
        """Test loading from legacy Django settings."""
        # Set legacy settings
        settings.PAYMENT_PROVIDER = 'stripe'
        settings.STRIPE_SECRET_KEY = 'sk_test_123'
        settings.EMAIL_PROVIDER = 'django'
        settings.SMS_PROVIDER = 'twilio'
        settings.TWILIO_ACCOUNT_SID = 'AC123'
        settings.TWILIO_AUTH_TOKEN = 'token'
        settings.TWILIO_FROM_NUMBER = '+15555551234'
        
        swaplayer_settings = SwapLayerSettings.from_django()
        
        assert swaplayer_settings.payments.provider == 'stripe'
        assert swaplayer_settings.payments.stripe.secret_key == 'sk_test_123'
        assert swaplayer_settings.email.provider == 'django'
        assert swaplayer_settings.sms.provider == 'twilio'


class TestValidation:
    @pytest.mark.xfail(reason="Needs proper Django settings mock setup")
    def test_validate_swaplayer_config_valid(self, settings):
        """Test validation with valid config."""
        settings.SWAPLAYER = SwapLayerSettings(
            payments={
                'provider': 'stripe',
                'stripe': {'secret_key': 'sk_test_123'}
            }
        )
        
        result = validate_swaplayer_config()
        assert result['valid'] is True
        assert 'modules' in result
        assert result['modules']['payments'].startswith('configured')
    
    @pytest.mark.xfail(reason="Needs proper Django settings mock setup")
    def test_validate_swaplayer_config_invalid(self, settings):
        """Test validation with invalid config."""
        # Remove SWAPLAYER setting to cause error
        if hasattr(settings, 'SWAPLAYER'):
            delattr(settings, 'SWAPLAYER')
        
        result = validate_swaplayer_config()
        # Should still be valid (empty config is valid)
        assert result['valid'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
