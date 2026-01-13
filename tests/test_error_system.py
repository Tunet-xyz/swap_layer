"""
Tests for SwapLayer rich error system.

Ensures error messages are helpful, actionable, and guide developers to solutions.
"""

import pytest

from swap_layer.exceptions import (
    EnvironmentVariableError,
    ErrorContext,
    ModuleNotConfiguredError,
    MultiTenantConfigError,
    ProviderConfigMismatchError,
    StripeKeyError,
    TwilioConfigError,
    WorkOSConfigError,
    format_startup_validation_errors,
)
from swap_layer.settings import SwapLayerSettings


class TestStripeKeyError:
    """Test Stripe API key error messages."""

    def test_invalid_secret_key_format(self):
        """Should provide helpful error for invalid Stripe secret key."""
        with pytest.raises(StripeKeyError) as exc_info:
            SwapLayerSettings(
                billing={
                    "provider": "stripe",
                    "stripe": {"secret_key": "pk_test_123abc"},  # Wrong! Publishable key
                }
            )

        error_message = str(exc_info.value)

        # Check error contains helpful elements
        assert "❌ Invalid Stripe secret key" in error_message
        assert "💡 Hint:" in error_message
        assert "pk_t" in error_message  # Shows prefix of what they provided
        assert "*" in error_message  # Shows value is masked
        assert "sk_test_" in error_message  # Shows correct format
        assert "sk_live_" in error_message  # Shows live example too
        assert "stripe.com/docs/keys" in error_message  # Documentation link
        assert "SWAPLAYER.billing.stripe.secret_key" in error_message  # Related setting
        # Ensure the full key is NOT exposed
        assert "pk_test_123abc" not in error_message

    def test_completely_wrong_key(self):
        """Should handle completely invalid key gracefully."""
        with pytest.raises(StripeKeyError):
            SwapLayerSettings(
                billing={"provider": "stripe", "stripe": {"secret_key": "totally_wrong_key_format"}}
            )


class TestTwilioConfigError:
    """Test Twilio configuration error messages."""

    def test_invalid_account_sid(self):
        """Should provide helpful error for invalid Twilio Account SID."""
        with pytest.raises(TwilioConfigError) as exc_info:
            SwapLayerSettings(
                communications={
                    "sms": {
                        "provider": "twilio",
                        "twilio": {
                            "account_sid": "XX1234567890abcdef1234567890abcd",  # Wrong! Should start with AC
                            "auth_token": "test_token",
                            "from_number": "+15555551234",
                        },
                    }
                }
            )

        error_message = str(exc_info.value)

        assert "❌ Invalid Twilio Account SID" in error_message
        assert "💡 Hint:" in error_message
        assert "XX12" in error_message  # Shows prefix of what they provided
        assert "*" in error_message  # Shows value is masked
        assert "AC" in error_message  # Shows correct prefix
        assert "twilio.com/docs" in error_message
        # Ensure the full Account SID is NOT exposed
        assert "XX1234567890abcdef1234567890abcd" not in error_message

    def test_invalid_phone_number_format(self):
        """Should provide helpful error for invalid phone number format."""
        with pytest.raises(TwilioConfigError) as exc_info:
            SwapLayerSettings(
                communications={
                    "sms": {
                        "provider": "twilio",
                        "twilio": {
                            "account_sid": "AC1234567890abcdef1234567890abcd",
                            "auth_token": "test_token",
                            "from_number": "555-123-4567",  # Wrong! Not E.164
                        },
                    }
                }
            )

        error_message = str(exc_info.value)

        assert "❌ Invalid phone number format" in error_message
        assert "E.164 format" in error_message
        # Should show format info but NOT the actual phone number
        assert "*" in error_message  # Shows value is masked
        assert "starts with '+': False" in error_message  # Shows format issue
        assert "+15555551234" in error_message  # US example
        assert "+442071838750" in error_message  # UK example
        assert "+61212345678" in error_message  # AU example
        # Ensure the full phone number is NOT exposed
        assert "555-123-4567" not in error_message or "555*" in error_message

    def test_phone_number_missing_plus(self):
        """Should catch phone numbers missing '+' prefix."""
        with pytest.raises(TwilioConfigError):
            SwapLayerSettings(
                communications={
                    "sms": {
                        "provider": "twilio",
                        "twilio": {
                            "account_sid": "AC1234567890abcdef1234567890abcd",
                            "auth_token": "test_token",
                            "from_number": "15555551234",  # Missing '+'
                        },
                    }
                }
            )


class TestWorkOSConfigError:
    """Test WorkOS configuration error messages."""

    def test_cookie_password_too_short(self):
        """Should provide helpful error for short cookie password."""
        with pytest.raises(WorkOSConfigError) as exc_info:
            SwapLayerSettings(
                identity={
                    "provider": "workos",
                    "workos_apps": {
                        "default": {
                            "api_key": "sk_test_123",
                            "client_id": "client_123",
                            "cookie_password": "short123",  # Only 8 chars, need 32+
                        }
                    },
                }
            )

        error_message = str(exc_info.value)

        assert "❌ Cookie password too short" in error_message
        assert "32 characters" in error_message
        assert "8 characters" in error_message  # Shows what they provided
        assert "secrets.token_urlsafe" in error_message  # Shows how to generate
        assert "openssl rand -base64" in error_message  # Alternative method

    def test_valid_cookie_password(self):
        """Should accept 32+ character cookie password."""
        # Should not raise
        config = SwapLayerSettings(
            identity={
                "provider": "workos",
                "workos_apps": {
                    "default": {
                        "api_key": "sk_test_123",
                        "client_id": "client_123",
                        "cookie_password": "a" * 32,  # Exactly 32 chars
                    }
                },
            }
        )
        assert config.identity.workos_apps["default"].cookie_password == "a" * 32


class TestProviderConfigMismatchError:
    """Test provider configuration mismatch errors."""

    def test_stripe_provider_without_config(self):
        """Should provide helpful error when Stripe provider selected but config missing."""
        with pytest.raises(ProviderConfigMismatchError) as exc_info:
            SwapLayerSettings(
                billing={
                    "provider": "stripe",
                    # Missing 'stripe' config!
                }
            )

        error_message = str(exc_info.value)

        assert "❌" in error_message
        assert "provider 'stripe' selected" in error_message
        assert "stripe not configured" in error_message
        assert "billing={'provider': 'stripe'" in error_message  # Shows example
        assert "'stripe': {" in error_message  # Shows what's missing

    def test_twilio_provider_without_config(self):
        """Should provide helpful error when Twilio provider selected but config missing."""
        with pytest.raises(ProviderConfigMismatchError):
            SwapLayerSettings(
                communications={
                    "sms": {
                        "provider": "twilio",
                        # Missing 'twilio' config!
                    }
                }
            )

    def test_workos_provider_without_apps(self):
        """Should provide helpful error when WorkOS provider selected but apps missing."""
        with pytest.raises(ProviderConfigMismatchError):
            SwapLayerSettings(
                identity={
                    "provider": "workos",
                    # Missing 'workos_apps' config!
                }
            )


class TestModuleNotConfiguredError:
    """Test module not configured errors."""

    def test_billing_not_configured(self):
        """Should provide helpful error when trying to use unconfigured module."""
        error = ModuleNotConfiguredError("billing")
        error_message = str(error)

        assert "❌ SwapLayer 'billing' module is not configured" in error_message
        assert "💡 Hint:" in error_message
        assert "billing={'provider': 'stripe'" in error_message  # Shows example
        assert "SWAPLAYER.billing" in error_message  # Shows setting to add

    def test_sms_not_configured(self):
        """Should provide helpful error for SMS module."""
        error = ModuleNotConfiguredError("communications")
        error_message = str(error)

        assert "'communications' module is not configured" in error_message
        assert "communications={'email':" in error_message or "communications=" in error_message


class TestEnvironmentVariableError:
    """Test environment variable errors."""

    def test_missing_env_var(self):
        """Should provide helpful error for missing environment variable."""
        error = EnvironmentVariableError("SWAPLAYER_STRIPE_SECRET_KEY")
        error_message = str(error)

        assert "❌ Missing or invalid environment variable" in error_message
        assert "SWAPLAYER_STRIPE_SECRET_KEY" in error_message
        assert "export SWAPLAYER_STRIPE_SECRET_KEY=" in error_message
        assert ".env file" in error_message

    def test_env_var_with_expected_format(self):
        """Should show expected format when provided."""
        error = EnvironmentVariableError(
            "TWILIO_FROM_NUMBER", expected_format="E.164 format (+15555551234)"
        )
        error_message = str(error)

        assert "Expected format: E.164 format" in error_message


class TestMultiTenantConfigError:
    """Test multi-tenant configuration errors."""

    def test_app_not_found(self):
        """Should provide helpful error when requested app doesn't exist."""
        error = MultiTenantConfigError("customer_portal", "workos", ["default", "admin"])
        error_message = str(error)

        assert "❌ App 'customer_portal' not found" in error_message
        assert "workos" in error_message
        assert "Available apps: default, admin" in error_message
        assert "'customer_portal': {" in error_message  # Shows how to add it

    def test_no_apps_configured(self):
        """Should handle case where no apps are configured."""
        error = MultiTenantConfigError("default", "auth0", [])
        error_message = str(error)

        assert "Available apps: none" in error_message


class TestErrorContext:
    """Test error context builder."""

    def test_build_config_error_context(self):
        """Should build comprehensive error context."""
        error = ValueError("Test error message")
        config = {
            "billing": {
                "provider": "stripe",
                "stripe": {"secret_key": "sk_test_123", "publishable_key": "pk_test_456"},
            }
        }

        context = ErrorContext.build_config_error_context(error, config)

        assert "🚨 SWAPLAYER CONFIGURATION ERROR" in context
        assert "Test error message" in context
        assert "📋 Your configuration:" in context
        assert "billing:" in context
        assert "provider: stripe" in context
        # Secrets should be masked
        assert "******** (masked)" in context
        assert "sk_test_123" not in context  # Secret key should be masked
        assert "Need help?" in context
        assert "github.com" in context

    def test_sensitive_keys_masked(self):
        """Should mask sensitive keys in configuration display."""
        config = {
            "api_key": "secret_key_123",
            "password": "my_password",
            "auth_token": "token_abc",
            "normal_field": "visible_value",
        }

        formatted = ErrorContext._format_config(config)

        # Sensitive fields should be masked
        assert "******** (masked)" in formatted
        assert "secret_key_123" not in formatted
        assert "my_password" not in formatted
        assert "token_abc" not in formatted

        # Normal fields should be visible
        assert "visible_value" in formatted


class TestStartupValidationErrors:
    """Test startup validation error formatting."""

    def test_format_multiple_validation_errors(self):
        """Should format multiple validation errors nicely."""
        errors = [
            {
                "loc": ("billing", "stripe", "secret_key"),
                "msg": "Stripe secret key must start with 'sk_'",
                "type": "value_error",
            },
            {
                "loc": ("sms", "twilio", "account_sid"),
                "msg": "Twilio Account SID must start with 'AC'",
                "type": "value_error",
            },
        ]

        formatted = format_startup_validation_errors(errors)

        assert "🚨 SWAPLAYER CONFIGURATION VALIDATION FAILED" in formatted
        assert "1. ❌ billing → stripe → secret_key" in formatted
        assert "2. ❌ sms → twilio → account_sid" in formatted
        assert "python manage.py swaplayer_check" in formatted
        assert "docs/README.md" in formatted
        assert "docs/architecture.md" in formatted


class TestRichErrorsInRealScenarios:
    """Test rich errors in realistic usage scenarios."""

    def test_developer_uses_wrong_stripe_key(self):
        """Simulate: Developer accidentally uses publishable key instead of secret key."""
        with pytest.raises(StripeKeyError) as exc_info:
            SwapLayerSettings(
                billing={
                    "provider": "stripe",
                    "stripe": {
                        "secret_key": "pk_test_51Abc123...",  # Oops! Used wrong key
                        "publishable_key": "pk_test_51Abc123...",
                    },
                }
            )

        # Error should be immediately obvious
        error = str(exc_info.value)
        assert "Invalid Stripe secret key" in error
        assert "pk_t" in error  # Shows prefix of what they used
        assert "*" in error  # Shows value is masked
        assert "sk_test_" in error  # Shows what they should use
        # Ensure full key is NOT exposed
        assert "pk_test_51Abc123" not in error

    def test_developer_copies_phone_number_wrong_format(self):
        """Simulate: Developer copies phone number from UI in wrong format."""
        with pytest.raises(TwilioConfigError) as exc_info:
            SwapLayerSettings(
                communications={
                    "sms": {
                        "provider": "twilio",
                        "twilio": {
                            "account_sid": "AC1234567890abcdef1234567890abcd",
                            "auth_token": "test_token",
                            "from_number": "(555) 123-4567",  # Copied from UI
                        },
                    }
                }
            )

        # Error should explain E.164 format
        error = str(exc_info.value)
        assert "E.164 format" in error
        assert "*" in error  # Phone number is masked
        assert "starts with '+': False" in error  # Shows format issue
        assert "+1" in error  # Shows proper format
        # Ensure full phone number is NOT exposed
        assert "(555) 123-4567" not in error or "(55*" in error

    def test_developer_uses_weak_cookie_password(self):
        """Simulate: Developer uses simple password instead of secure random."""
        with pytest.raises(WorkOSConfigError) as exc_info:
            SwapLayerSettings(
                identity={
                    "provider": "workos",
                    "workos_apps": {
                        "default": {
                            "api_key": "sk_test_123",
                            "client_id": "client_123",
                            "cookie_password": "password123",  # Too weak!
                        }
                    },
                }
            )

        # Error should explain how to generate secure password
        error = str(exc_info.value)
        assert "32 characters" in error
        assert "secrets.token_urlsafe" in error or "openssl rand" in error

    def test_developer_forgets_provider_config(self):
        """Simulate: Developer sets provider but forgets the actual config."""
        with pytest.raises(ProviderConfigMismatchError) as exc_info:
            SwapLayerSettings(
                billing={"provider": "stripe"}  # Forgot the stripe config!
            )

        # Error should show complete example
        error = str(exc_info.value)
        assert "provider 'stripe' selected" in error
        assert "'stripe': {" in error  # Shows they need to add this
        assert "secret_key" in error  # Shows what goes in the config


class TestErrorInheritance:
    """Test that errors inherit correctly for catch-all handling."""

    def test_all_config_errors_inherit_from_base(self):
        """All configuration errors should inherit from ConfigurationError."""
        from swap_layer.exceptions import ConfigurationError

        assert issubclass(StripeKeyError, ConfigurationError)
        assert issubclass(TwilioConfigError, ConfigurationError)
        assert issubclass(WorkOSConfigError, ConfigurationError)
        assert issubclass(ProviderConfigMismatchError, ConfigurationError)
        assert issubclass(ModuleNotConfiguredError, ConfigurationError)

    def test_can_catch_all_swaplayer_errors(self):
        """Should be able to catch all SwapLayer errors with base exception."""
        from swap_layer.exceptions import SwapLayerError

        with pytest.raises(SwapLayerError):
            SwapLayerSettings(
                billing={"provider": "stripe", "stripe": {"secret_key": "invalid_key"}}
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
