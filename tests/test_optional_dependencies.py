"""
Test that optional dependencies are truly optional.

This ensures users can use SwapLayer modules independently without installing
all provider dependencies (e.g., use WorkOS without Stripe installed).
"""
import builtins
import sys


class BlockImport:
    """Context manager to temporarily block specific imports for testing."""

    def __init__(self, *blocked_modules):
        self.blocked_modules = blocked_modules
        self.original_import = None

    def __enter__(self):
        self.original_import = builtins.__import__

        def custom_import(name, *args, **kwargs):
            if any(name == blocked or name.startswith(f"{blocked}.")
                   for blocked in self.blocked_modules):
                raise ImportError(f"No module named '{name}' (blocked by test)")
            return self.original_import(name, *args, **kwargs)

        builtins.__import__ = custom_import
        return self

    def __exit__(self, *args):
        builtins.__import__ = self.original_import


def test_can_use_workos_without_stripe():
    """Test that WorkOS can be configured and imported without Stripe installed."""
    # Save original stripe modules
    stripe_modules = {key: sys.modules[key] for key in list(sys.modules.keys()) if key.startswith('stripe')}

    try:
        # Remove stripe from sys.modules temporarily
        for mod in list(stripe_modules.keys()):
            if mod in sys.modules:
                del sys.modules[mod]

        with BlockImport('stripe'):
            # These imports should succeed even without stripe
            from swap_layer.settings import SwapLayerSettings

            # Should be able to configure WorkOS
            settings = SwapLayerSettings(
                identity={
                    'provider': 'workos',
                    'workos_apps': {
                        'default': {
                            'api_key': 'sk_test_123',
                            'client_id': 'client_123',
                            'cookie_password': 'a' * 32
                        }
                    }
                }
            )

            assert settings.identity.provider == 'workos'
            assert 'default' in settings.identity.workos_apps
    finally:
        # Restore original stripe modules
        sys.modules.update(stripe_modules)


def test_can_use_stripe_without_twilio():
    """Test that Stripe billing can be configured and imported without Twilio installed."""
    # Save original twilio modules
    twilio_modules = {key: sys.modules[key] for key in list(sys.modules.keys()) if key.startswith('twilio')}

    try:
        # Remove twilio from sys.modules temporarily
        for mod in list(twilio_modules.keys()):
            if mod in sys.modules:
                del sys.modules[mod]

        with BlockImport('twilio'):
            # These imports should succeed even without twilio
            from swap_layer.settings import SwapLayerSettings

            # Should be able to configure Stripe
            settings = SwapLayerSettings(
                billing={
                    'provider': 'stripe',
                    'stripe': {
                        'secret_key': 'sk_test_123'
                    }
                }
            )

            assert settings.billing.provider == 'stripe'
            assert settings.billing.stripe.secret_key == 'sk_test_123'
    finally:
        # Restore original twilio modules
        sys.modules.update(twilio_modules)


def test_can_use_twilio_without_workos():
    """Test that Twilio SMS can be configured and imported without WorkOS installed."""
    # Save original workos modules
    workos_modules = {key: sys.modules[key] for key in list(sys.modules.keys()) if key.startswith('workos')}

    try:
        # Remove workos from sys.modules temporarily
        for mod in list(workos_modules.keys()):
            if mod in sys.modules:
                del sys.modules[mod]

        with BlockImport('workos'):
            # These imports should succeed even without workos
            from swap_layer.settings import SwapLayerSettings

            # Should be able to configure Twilio
            settings = SwapLayerSettings(
                communications={
                    'sms': {
                        'provider': 'twilio',
                        'twilio': {
                            'account_sid': 'ACxxxxxxxx',
                            'auth_token': 'test_token',
                            'from_number': '+1234567890'
                        }
                    }
                }
            )

            assert settings.communications.sms.provider == 'twilio'
    finally:
        # Restore original workos modules
        sys.modules.update(workos_modules)


def test_lazy_import_pattern_works():
    """Test that the lazy import pattern using __getattr__ works correctly."""
    # Test that importing from providers module works
    from swap_layer.billing.providers import StripePaymentProvider
    assert StripePaymentProvider is not None

    from swap_layer.identity.platform.providers import WorkOSClient
    assert WorkOSClient is not None

    # Test that lazy imports don't eagerly load the module
    # We can't easily test AttributeError for invalid imports because Python's
    # import system will raise ImportError before our __getattr__ is called
