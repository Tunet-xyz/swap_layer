"""
Django models and Pydantic schemas for identity platform provider metadata.

These models help you map external OAuth/OIDC identities to your Django users
while maintaining provider independence.
"""

import uuid
from datetime import datetime
from typing import Any

from django.conf import settings
from django.db import models
from pydantic import BaseModel, ConfigDict, Field


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
            ("workos", "WorkOS"),
            ("auth0", "Auth0"),
        ],
        help_text="OAuth/OIDC provider",
    )
    provider_user_id = models.CharField(
        max_length=255, db_index=True, help_text="User ID from identity provider"
    )
    provider_email = models.EmailField(
        blank=True, null=True, help_text="Email from identity provider"
    )
    provider_name = models.CharField(
        max_length=255, blank=True, null=True, help_text="Name from identity provider"
    )
    provider_access_token = models.TextField(
        blank=True, null=True, help_text="OAuth access token (store encrypted in production)"
    )
    provider_refresh_token = models.TextField(
        blank=True, null=True, help_text="OAuth refresh token (store encrypted in production)"
    )
    provider_token_expires_at = models.DateTimeField(
        blank=True, null=True, help_text="When the access token expires"
    )
    provider_metadata = models.JSONField(
        default=dict, blank=True, help_text="Additional provider data"
    )
    last_login_at = models.DateTimeField(
        auto_now=True, help_text="Last time user authenticated via this provider"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When the identity was first linked"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["identity_provider", "provider_user_id"]),
            models.Index(fields=["provider_email"]),
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
            ("workos", "WorkOS"),
            ("auth0", "Auth0"),
        ],
        help_text="SSO provider",
    )
    sso_connection_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text="SSO connection ID from provider",
    )
    sso_organization_id = models.CharField(
        max_length=255, blank=True, null=True, help_text="Organization ID from provider"
    )
    sso_enabled = models.BooleanField(
        default=False, help_text="Whether SSO is enabled for this organization"
    )
    sso_domain = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Email domain for SSO (e.g., 'company.com')",
    )
    sso_metadata = models.JSONField(
        default=dict, blank=True, help_text="Additional SSO configuration"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["sso_provider", "sso_connection_id"]),
            models.Index(fields=["sso_domain"]),
        ]


# Pydantic model for internal data transfer
class UserIdentity(BaseModel):
    """
    Pydantic model representing a user identity mapping.
    Used internally for data transfer between operations and repositories.
    """

    id: uuid.UUID | None = Field(default_factory=uuid.uuid4)
    user_id: str = Field(..., description="Internal user ID")
    provider: str = Field(..., description="Identity provider name (e.g., 'workos', 'auth0')")
    provider_user_id: str = Field(..., description="User ID from the provider")
    email: str | None = Field(None, description="Email from provider")
    data: dict[str, Any] = Field(default_factory=dict, description="Additional provider data")
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# Django model for database persistence
class AbstractUserIdentity(models.Model):
    """
    Abstract Django model for User Identity mapping.
    Maps an external Identity Provider user to an internal Django User.

    Inherit from this model to create your own UserIdentity table:

        from swap_layer.identity.platform.models import AbstractUserIdentity

        class UserIdentity(AbstractUserIdentity):
            class Meta:
                db_table = 'user_identities'
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="identities"
    )
    provider = models.CharField(max_length=50)  # e.g. 'workos', 'auth0'
    provider_user_id = models.CharField(max_length=255)

    # Optional: Store extra data from the provider
    email = models.EmailField(null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        unique_together = ("provider", "provider_user_id")
        indexes = [
            models.Index(fields=["provider", "provider_user_id"]),
        ]

    def __str__(self):
        return f"{self.provider}:{self.provider_user_id} -> {self.user}"

    @classmethod
    def from_dto(cls, dto: UserIdentity, user_instance) -> "AbstractUserIdentity":
        """Create Django model instance from Pydantic DTO."""
        return cls(
            id=dto.id,
            user=user_instance,
            provider=dto.provider,
            provider_user_id=dto.provider_user_id,
            email=dto.email,
            data=dto.data,
        )

    def to_dto(self) -> UserIdentity:
        """Convert Django model instance to Pydantic DTO."""
        return UserIdentity(
            id=self.id,
            user_id=str(self.user.pk),
            provider=self.provider,
            provider_user_id=self.provider_user_id,
            email=self.email,
            data=self.data,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
