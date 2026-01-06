"""
SwapLayer Settings Management

Provides a structured, validated, and developer-friendly way to manage
SwapLayer configuration across all modules.

Usage:
    # In your Django settings.py
    from swap_layer.settings import SwapLayerSettings
    
    SWAPLAYER = SwapLayerSettings(
        payments={
            'provider': 'stripe',
            'stripe': {
                'secret_key': os.environ['STRIPE_SECRET_KEY'],
                'publishable_key': os.environ.get('STRIPE_PUBLISHABLE_KEY'),
            }
        },
        email={
            'provider': 'django',
        },
        # ... other modules
    )
    
    # Or use environment variables with SWAPLAYER_ prefix
    SWAPLAYER = SwapLayerSettings.from_env()
"""

import os
from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError as PydanticValidationError
from django.core.exceptions import ImproperlyConfigured
from .exceptions import (
    StripeKeyError,
    TwilioConfigError,
    WorkOSConfigError,
    ProviderConfigMismatchError,
    ErrorContext,
    format_startup_validation_errors,
)


# ============================================================================
# Module Configuration Classes
# ============================================================================

class StripeConfig(BaseModel):
    """Stripe payment provider configuration."""
    secret_key: str = Field(..., description="Stripe secret key (required)")
    publishable_key: Optional[str] = Field(None, description="Stripe publishable key (optional)")
    webhook_secret: Optional[str] = Field(None, description="Stripe webhook signing secret")
    
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v.startswith('sk_'):
            raise StripeKeyError('secret key', v)
        return v


class PaymentsConfig(BaseModel):
    """Payment module configuration."""
    provider: Literal['stripe'] = Field('stripe', description="Payment provider to use")
    stripe: Optional[StripeConfig] = Field(None, description="Stripe configuration")
    
    @model_validator(mode='after')
    def validate_provider_config(self):
        if self.provider == 'stripe' and not self.stripe:
            raise ProviderConfigMismatchError('payments', 'stripe', 'stripe')
        return self


class EmailConfig(BaseModel):
    """Email module configuration."""
    provider: Literal['django', 'smtp'] = Field('django', description="Email provider to use")
    # Django/Anymail uses Django's EMAIL_BACKEND and ANYMAIL settings
    # SMTP uses Django's EMAIL_HOST, EMAIL_PORT, etc.


class TwilioConfig(BaseModel):
    """Twilio SMS provider configuration."""
    account_sid: str = Field(..., description="Twilio Account SID")
    auth_token: str = Field(..., description="Twilio Auth Token")
    from_number: str = Field(..., description="Twilio phone number (E.164 format)")
    
    @field_validator('from_number')
    @classmethod
    def validate_phone_number(cls, v: str) -> str:
        if not v.startswith('+'):
            raise TwilioConfigError.invalid_phone_number(v)
        return v
    
    @field_validator('account_sid')
    @classmethod
    def validate_account_sid(cls, v: str) -> str:
        if not v.startswith('AC'):
            raise TwilioConfigError.invalid_account_sid(v)
        return v


class SNSConfig(BaseModel):
    """AWS SNS SMS provider configuration."""
    aws_access_key_id: Optional[str] = Field(None, description="AWS Access Key ID (optional if using IAM)")
    aws_secret_access_key: Optional[str] = Field(None, description="AWS Secret Access Key")
    region_name: str = Field('us-east-1', description="AWS region")
    sender_id: Optional[str] = Field(None, description="SMS Sender ID")


class SMSConfig(BaseModel):
    """SMS module configuration."""
    provider: Literal['twilio', 'sns'] = Field('twilio', description="SMS provider to use")
    twilio: Optional[TwilioConfig] = Field(None, description="Twilio configuration")
    sns: Optional[SNSConfig] = Field(None, description="AWS SNS configuration")
    
    @model_validator(mode='after')
    def validate_provider_config(self):
        if self.provider == 'twilio' and not self.twilio:
            raise ProviderConfigMismatchError('sms', 'twilio', 'twilio')
        if self.provider == 'sns' and not self.sns:
            raise ProviderConfigMismatchError('sms', 'sns', 'sns')
        return self


class StorageConfig(BaseModel):
    """Storage module configuration."""
    provider: Literal['local', 'django'] = Field('local', description="Storage provider to use")
    media_root: Optional[str] = Field(None, description="Local storage root directory")
    media_url: Optional[str] = Field('/media/', description="Media URL prefix")
    # Django-storages uses DEFAULT_FILE_STORAGE and storage backend settings


class WorkOSAppConfig(BaseModel):
    """WorkOS application configuration."""
    api_key: str = Field(..., description="WorkOS API key")
    client_id: str = Field(..., description="WorkOS client ID")
    cookie_password: str = Field(..., description="Cookie encryption password (32+ chars)")
    
    @field_validator('cookie_password')
    @classmethod
    def validate_cookie_password(cls, v: str) -> str:
        if len(v) < 32:
            raise WorkOSConfigError.short_cookie_password(len(v))
        return v


class Auth0AppConfig(BaseModel):
    """Auth0 application configuration."""
    client_id: str = Field(..., description="Auth0 client ID")
    client_secret: str = Field(..., description="Auth0 client secret")


class IdentityPlatformConfig(BaseModel):
    """Identity/OAuth module configuration."""
    provider: Literal['workos', 'auth0'] = Field('workos', description="Identity provider to use")
    workos_apps: Optional[Dict[str, WorkOSAppConfig]] = Field(None, description="WorkOS app configurations")
    auth0_apps: Optional[Dict[str, Auth0AppConfig]] = Field(None, description="Auth0 app configurations")
    auth0_domain: Optional[str] = Field(None, description="Auth0 domain (required for Auth0)")
    
    @model_validator(mode='after')
    def validate_provider_config(self):
        if self.provider == 'workos' and not self.workos_apps:
            raise ProviderConfigMismatchError('identity', 'workos', 'workos_apps')
        if self.provider == 'auth0':
            if not self.auth0_apps:
                raise ProviderConfigMismatchError('identity', 'auth0', 'auth0_apps')
            if not self.auth0_domain:
                raise ProviderConfigMismatchError('identity', 'auth0', 'auth0_domain')
        return self


class IdentityVerificationConfig(BaseModel):
    """Identity verification module configuration."""
    provider: Literal['stripe'] = Field('stripe', description="Verification provider to use")
    stripe_secret_key: Optional[str] = Field(None, description="Stripe secret key for identity verification")
    
    @model_validator(mode='after')
    def validate_provider_config(self):
        if self.provider == 'stripe' and not self.stripe_secret_key:
            raise ProviderConfigMismatchError('verification', 'stripe', 'stripe_secret_key')
        return self


# ============================================================================
# Main Settings Class
# ============================================================================

class SwapLayerSettings(BaseModel):
    """
    SwapLayer unified settings configuration.
    
    Provides structured, validated configuration for all SwapLayer modules
    with helpful error messages and type safety.
    
    Example:
        # settings.py
        SWAPLAYER = SwapLayerSettings(
            payments={'provider': 'stripe', 'stripe': {'secret_key': 'sk_test_...'}},
            email={'provider': 'django'},
            sms={'provider': 'twilio', 'twilio': {...}},
        )
    """
    
    # Module configurations
    payments: Optional[PaymentsConfig] = Field(None, description="Payment module configuration")
    email: Optional[EmailConfig] = Field(None, description="Email module configuration")
    sms: Optional[SMSConfig] = Field(None, description="SMS module configuration")
    storage: Optional[StorageConfig] = Field(None, description="Storage module configuration")
    identity: Optional[IdentityPlatformConfig] = Field(None, description="Identity/OAuth configuration")
    verification: Optional[IdentityVerificationConfig] = Field(None, description="Identity verification configuration")
    
    # Global settings
    debug: bool = Field(False, description="Enable debug mode for verbose logging")
    raise_on_error: bool = Field(True, description="Raise exceptions on provider errors")
    
    model_config = {
        'extra': 'forbid',  # Prevent typos in configuration
        'validate_assignment': True,
    }
    
    @classmethod
    def from_env(cls, prefix: str = 'SWAPLAYER_') -> 'SwapLayerSettings':
        """
        Load configuration from environment variables.
        
        Environment variables should be prefixed with SWAPLAYER_ (or custom prefix).
        
        Examples:
            SWAPLAYER_PAYMENTS_PROVIDER=stripe
            SWAPLAYER_PAYMENTS_STRIPE_SECRET_KEY=sk_test_...
            SWAPLAYER_EMAIL_PROVIDER=django
            SWAPLAYER_SMS_PROVIDER=twilio
            SWAPLAYER_SMS_TWILIO_ACCOUNT_SID=AC...
            SWAPLAYER_SMS_TWILIO_AUTH_TOKEN=...
            SWAPLAYER_SMS_TWILIO_FROM_NUMBER=+1555...
        
        Args:
            prefix: Environment variable prefix (default: 'SWAPLAYER_')
            
        Returns:
            Configured SwapLayerSettings instance
        """
        config: Dict[str, Any] = {}
        
        # Parse environment variables into nested config structure
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue
            
            # Remove prefix and split into parts
            parts = key[len(prefix):].lower().split('_')
            
            # Build nested dictionary
            current = config
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        
        try:
            return cls(**config)
        except PydanticValidationError as e:
            # Enhance validation errors with rich context
            print(format_startup_validation_errors(e.errors()))
            print(ErrorContext.build_config_error_context(e, config))
            raise
    
    @classmethod
    def from_django(cls) -> 'SwapLayerSettings':
        """
        Load configuration from Django settings.
        
        Looks for a SWAPLAYER dictionary in Django settings, or falls back
        to legacy individual settings for backward compatibility.
        
        Example Django settings:
            # New way (recommended)
            SWAPLAYER = {
                'payments': {'provider': 'stripe', 'stripe': {'secret_key': 'sk_...'}},
                'email': {'provider': 'django'},
            }
            
            # Old way (still supported for backward compatibility)
            PAYMENT_PROVIDER = 'stripe'
            STRIPE_SECRET_KEY = 'sk_...'
        """
        from django.conf import settings
        
        # Check for new SWAPLAYER config
        if hasattr(settings, 'SWAPLAYER'):
            swaplayer_config = settings.SWAPLAYER
            if isinstance(swaplayer_config, dict):
                return cls(**swaplayer_config)
            elif isinstance(swaplayer_config, cls):
                return swaplayer_config
        
        # Fall back to legacy settings for backward compatibility
        return cls._from_legacy_django_settings(settings)
    
    @classmethod
    def _from_legacy_django_settings(cls, settings) -> 'SwapLayerSettings':
        """Build config from legacy Django settings for backward compatibility."""
        config: Dict[str, Any] = {}
        
        # Payments
        if hasattr(settings, 'PAYMENT_PROVIDER'):
            config['payments'] = {
                'provider': getattr(settings, 'PAYMENT_PROVIDER', 'stripe'),
            }
            if hasattr(settings, 'STRIPE_SECRET_KEY'):
                config['payments']['stripe'] = {
                    'secret_key': settings.STRIPE_SECRET_KEY,
                    'publishable_key': getattr(settings, 'STRIPE_PUBLISHABLE_KEY', None),
                }
        
        # Email
        if hasattr(settings, 'EMAIL_PROVIDER'):
            config['email'] = {
                'provider': getattr(settings, 'EMAIL_PROVIDER', 'django'),
            }
        
        # SMS
        if hasattr(settings, 'SMS_PROVIDER'):
            sms_provider = settings.SMS_PROVIDER
            config['sms'] = {'provider': sms_provider}
            
            if sms_provider == 'twilio' and hasattr(settings, 'TWILIO_ACCOUNT_SID'):
                config['sms']['twilio'] = {
                    'account_sid': settings.TWILIO_ACCOUNT_SID,
                    'auth_token': settings.TWILIO_AUTH_TOKEN,
                    'from_number': settings.TWILIO_FROM_NUMBER,
                }
        
        # Storage
        if hasattr(settings, 'STORAGE_PROVIDER'):
            config['storage'] = {
                'provider': getattr(settings, 'STORAGE_PROVIDER', 'local'),
                'media_root': getattr(settings, 'MEDIA_ROOT', None),
                'media_url': getattr(settings, 'MEDIA_URL', '/media/'),
            }
        
        # Identity Platform
        if hasattr(settings, 'IDENTITY_PROVIDER'):
            identity_provider = settings.IDENTITY_PROVIDER
            config['identity'] = {'provider': identity_provider}
            
            if identity_provider == 'workos' and hasattr(settings, 'WORKOS_APPS'):
                config['identity']['workos_apps'] = settings.WORKOS_APPS
            elif identity_provider == 'auth0' and hasattr(settings, 'AUTH0_APPS'):
                config['identity']['auth0_apps'] = settings.AUTH0_APPS
                config['identity']['auth0_domain'] = getattr(settings, 'AUTH0_DEVELOPER_DOMAIN', None)
        
        # Identity Verification
        if hasattr(settings, 'IDENTITY_VERIFICATION_PROVIDER'):
            config['verification'] = {
                'provider': getattr(settings, 'IDENTITY_VERIFICATION_PROVIDER', 'stripe'),
                'stripe_secret_key': getattr(settings, 'STRIPE_SECRET_KEY', None),
            }
        
        try:
            return cls(**config) if config else cls()
        except PydanticValidationError as e:
            # Enhance validation errors with rich context
            print(format_startup_validation_errors(e.errors()))
            print(ErrorContext.build_config_error_context(e, config))
            raise
    
    def validate_module(self, module: str) -> None:
        """
        Validate that a specific module is properly configured.
        
        Args:
            module: Module name ('payments', 'email', 'sms', etc.)
            
        Raises:
            ImproperlyConfigured: If module is not configured or invalid
        """
        from .exceptions import ModuleNotConfiguredError
        
        module_config = getattr(self, module, None)
        if module_config is None:
            raise ModuleNotConfiguredError(module)
    
    def get_status(self) -> Dict[str, str]:
        """
        Get configuration status for all modules.
        
        Returns:
            Dictionary mapping module names to status ('configured', 'not configured', 'invalid')
        """
        status = {}
        for module in ['payments', 'email', 'sms', 'storage', 'identity', 'verification']:
            config = getattr(self, module, None)
            if config is None:
                status[module] = 'not configured'
            else:
                try:
                    # Re-validate to catch any issues
                    config.model_validate(config)
                    status[module] = f"configured (provider: {config.provider})"
                except Exception as e:
                    status[module] = f'invalid: {str(e)}'
        return status
    
    def __repr__(self) -> str:
        """Pretty representation showing configured modules."""
        status = self.get_status()
        configured = [k for k, v in status.items() if v.startswith('configured')]
        return f"<SwapLayerSettings: {', '.join(configured) or 'no modules configured'}>"


# ============================================================================
# Helper Functions
# ============================================================================

def get_swaplayer_settings() -> SwapLayerSettings:
    """
    Get the SwapLayer settings instance from Django settings.
    
    Returns:
        SwapLayerSettings instance
        
    Raises:
        ImproperlyConfigured: If SwapLayer is not configured in Django settings
    """
    from django.conf import settings
    
    if not hasattr(settings, '_swaplayer_settings_cache'):
        settings._swaplayer_settings_cache = SwapLayerSettings.from_django()
    
    return settings._swaplayer_settings_cache


def validate_swaplayer_config() -> Dict[str, Any]:
    """
    Validate SwapLayer configuration and return detailed status.
    
    Useful for Django management commands and health checks.
    
    Returns:
        Dictionary with validation results
    """
    try:
        settings = get_swaplayer_settings()
        status = settings.get_status()
        
        return {
            'valid': True,
            'modules': status,
            'settings': settings,
        }
    except Exception as e:
        return {
            'valid': False,
            'error': str(e),
            'modules': {},
        }
