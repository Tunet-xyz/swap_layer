"""
Django model mixins for storing identity platform provider metadata.

These mixins help you map external OAuth/OIDC identities to your Django users
while maintaining provider independence.
"""

from django.db import models
from django.utils import timezone


class OAuthIdentityMixin(models.Model):
    """
    Mixin for storing OAuth/OIDC identity provider data.
    
    Add this to your User model or create a separate UserIdentity model:
    
        from swap_layer.identity.platform.models import OAuthIdentityMixin
        
        class UserIdentity(OAuthIdentityMixin, models.Model):
            user = models.ForeignKey(User, on_delete=models.CASCADE)
            # ... your fields
    """
    identity_provider = models.CharField(
        max_length=50,
        db_index=True,
        choices=[
            ('workos', 'WorkOS'),
            ('auth0', 'Auth0'),
        ],
        help_text="OAuth/OIDC provider"
    )
    provider_user_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="User ID from identity provider"
    )
    provider_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email from identity provider"
    )
    provider_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Name from identity provider"
    )
    provider_access_token = models.TextField(
        blank=True,
        null=True,
        help_text="OAuth access token (store encrypted in production)"
    )
    provider_refresh_token = models.TextField(
        blank=True,
        null=True,
        help_text="OAuth refresh token (store encrypted in production)"
    )
    provider_token_expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the access token expires"
    )
    provider_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional provider data"
    )
    last_login_at = models.DateTimeField(
        auto_now=True,
        help_text="Last time user authenticated via this provider"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the identity was first linked"
    )
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['identity_provider', 'provider_user_id']),
            models.Index(fields=['provider_email']),
        ]
        # For separate UserIdentity model, add:
        # unique_together = [['identity_provider', 'provider_user_id']]


class SSOConnectionMixin(models.Model):
    """
    Mixin for storing SSO connection data (for WorkOS organizations).
    
    Add this to your Organization or Tenant model:
    
        from swap_layer.identity.platform.models import SSOConnectionMixin
        
        class Organization(SSOConnectionMixin, models.Model):
            name = models.CharField(max_length=255)
            # ... your fields
    """
    sso_provider = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('workos', 'WorkOS'),
            ('auth0', 'Auth0'),
        ],
        help_text="SSO provider"
    )
    sso_connection_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text="SSO connection ID from provider"
    )
    sso_organization_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Organization ID from provider"
    )
    sso_enabled = models.BooleanField(
        default=False,
        help_text="Whether SSO is enabled for this organization"
    )
    sso_domain = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Email domain for SSO (e.g., 'company.com')"
    )
    sso_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional SSO configuration"
    )
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['sso_provider', 'sso_connection_id']),
            models.Index(fields=['sso_domain']),
        ]

