"""
Pytest configuration for SwapLayer tests.

Configures Django settings before running tests.
"""
import os
import django
from django.conf import settings


def pytest_configure():
    """Configure Django settings for tests."""
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
            ],
            # Email settings
            EMAIL_PROVIDER='django',
            EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
            
            # Payment settings
            PAYMENT_PROVIDER='stripe',
            STRIPE_SECRET_KEY='sk_test_mock',
            STRIPE_PUBLISHABLE_KEY='pk_test_mock',
            
            # Storage settings
            STORAGE_PROVIDER='local',
            MEDIA_ROOT='/tmp/test_media',
            MEDIA_URL='/media/',
            
            # SMS settings
            SMS_PROVIDER='twilio',
            TWILIO_ACCOUNT_SID='AC_test',
            TWILIO_AUTH_TOKEN='token_test',
            TWILIO_FROM_NUMBER='+15555551234',
            
            # Identity Platform settings
            IDENTITY_PROVIDER='workos',
            WORKOS_API_KEY='sk_test',
            WORKOS_CLIENT_ID='client_test',
            
            AUTH0_DOMAIN='test.auth0.com',
            AUTH0_CLIENT_ID='auth0_test',
            AUTH0_CLIENT_SECRET='auth0_secret_test',
            
            # Identity Verification settings
            IDENTITY_VERIFICATION_PROVIDER='stripe',
            STRIPE_IDENTITY_SECRET_KEY='sk_test_identity',
            
            SECRET_KEY='test-secret-key-for-testing-only',
            USE_TZ=True,
        )
        django.setup()
