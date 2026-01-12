"""
Django models and Pydantic schemas for identity verification provider metadata.

These models help you track KYC/identity verification sessions and results
while maintaining provider independence.
"""

from datetime import datetime
from typing import Any

from django.conf import settings
from django.db import models
from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Pydantic Schemas (for API/data transfer)
# =============================================================================


class VerificationSessionCreate(BaseModel):
    """Input schema for creating a verification session."""

    verification_type: str = Field(default="document", pattern="^(document|id_number)$")
    return_url: str | None = None
    email: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WebhookPayload(BaseModel):
    """Schema for webhook payloads from providers."""

    raw_body: bytes
    signature: str
    headers: dict[str, Any]


# =============================================================================
# Django Model Mixins
# =============================================================================


class IdentityVerificationMixin(models.Model):
    """
    Mixin for storing identity verification session data.

    Add this to your User model or create a separate IdentityVerification model:

        from swap_layer.identity.verification.models import IdentityVerificationMixin

        class IdentityVerification(IdentityVerificationMixin, models.Model):
            user = models.ForeignKey(User, on_delete=models.CASCADE)
            # ... your fields
    """

    verification_provider = models.CharField(
        max_length=50,
        db_index=True,
        choices=[
            ("stripe", "Stripe Identity"),
            ("onfido", "Onfido"),
        ],
        help_text="Identity verification provider",
    )
    verification_session_id = models.CharField(
        max_length=255, db_index=True, help_text="Session ID from verification provider"
    )
    verification_status = models.CharField(
        max_length=50,
        default="requires_input",
        choices=[
            ("requires_input", "Requires Input"),
            ("processing", "Processing"),
            ("verified", "Verified"),
            ("canceled", "Canceled"),
        ],
        help_text="Current verification status",
    )
    verification_type = models.CharField(
        max_length=50,
        default="document",
        choices=[
            ("document", "Document"),
            ("id_number", "ID Number"),
        ],
        help_text="Type of verification",
    )
    client_secret = models.CharField(
        max_length=500, blank=True, null=True, help_text="Client secret for frontend integration"
    )
    verification_url = models.URLField(
        max_length=500, blank=True, null=True, help_text="URL for user to complete verification"
    )

    # Verified data fields
    verified_first_name = models.CharField(
        max_length=100, blank=True, null=True, help_text="First name from verified document"
    )
    verified_last_name = models.CharField(
        max_length=100, blank=True, null=True, help_text="Last name from verified document"
    )
    verified_date_of_birth = models.DateField(
        blank=True, null=True, help_text="Date of birth from verified document"
    )
    verified_address_line1 = models.CharField(
        max_length=255, blank=True, null=True, help_text="Address line 1 from verified document"
    )
    verified_address_city = models.CharField(
        max_length=100, blank=True, null=True, help_text="City from verified document"
    )
    verified_address_postal_code = models.CharField(
        max_length=20, blank=True, null=True, help_text="Postal code from verified document"
    )
    verified_address_country = models.CharField(
        max_length=2, blank=True, null=True, help_text="Country code from verified document"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When verification session was created"
    )
    verified_at = models.DateTimeField(
        blank=True, null=True, help_text="When verification was completed"
    )

    # Metadata
    verification_metadata = models.JSONField(
        default=dict, blank=True, help_text="Additional verification data from provider"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["verification_provider", "verification_session_id"]),
            models.Index(fields=["verification_status"]),
            models.Index(fields=["-created_at"]),
        ]


# Pydantic model for internal data transfer
class IdentityVerificationSession(BaseModel):
    """
    Pydantic model representing an identity verification session.
    Used internally for data transfer between operations and repositories.
    """

    user_id: str = Field(..., description="Internal user ID")
    provider: str = Field(..., description="Verification provider name (e.g., 'stripe')")
    provider_session_id: str = Field(..., description="Session ID from the provider")
    status: str = Field(..., description="Verification status")
    verification_type: str = Field(..., description="Type of verification")
    client_secret: str = Field(default="", description="Client secret for frontend integration")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    verification_report_id: str | None = Field(
        None, description="Provider's verification report ID"
    )
    verified_at: datetime | None = Field(None, description="When verification was completed")
    verified_first_name: str | None = None
    verified_last_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# Django model for database persistence
class AbstractIdentityVerificationSession(models.Model):
    """
    Abstract Django model for identity verification session persistence.
    Maps verification sessions to Django users.

    Inherit from this model to create your own verification table:

        from swap_layer.identity.verification.models import AbstractIdentityVerificationSession

        class IdentityVerification(AbstractIdentityVerificationSession):
            class Meta:
                db_table = 'identity_verifications'
    """

    provider_session_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Session ID from the identity provider",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="identity_verifications"
    )

    status = models.CharField(max_length=50, db_index=True)
    verification_type = models.CharField(max_length=50)
    provider = models.CharField(max_length=50)

    client_secret = models.CharField(max_length=255, blank=True, null=True)
    verification_report_id = models.CharField(max_length=255, blank=True, null=True)

    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Store the full metadata blob
    metadata = models.JSONField(default=dict, blank=True)

    # Simplified Verified Data
    verified_first_name = models.CharField(max_length=255, blank=True)
    verified_last_name = models.CharField(max_length=255, blank=True)

    class Meta:
        abstract = True

    @classmethod
    def from_dto(
        cls, dto: IdentityVerificationSession, user_instance
    ) -> "AbstractIdentityVerificationSession":
        """Create Django model instance from Pydantic DTO."""
        return cls(
            user=user_instance,
            provider_session_id=dto.provider_session_id,
            status=dto.status,
            verification_type=dto.verification_type,
            provider=dto.provider,
            client_secret=dto.client_secret,
            metadata=dto.metadata,
            verification_report_id=dto.verification_report_id,
            verified_at=dto.verified_at,
            verified_first_name=dto.verified_first_name,
            verified_last_name=dto.verified_last_name,
        )

    def to_dto(self) -> IdentityVerificationSession:
        """Convert Django model instance to Pydantic DTO."""
        return IdentityVerificationSession(
            user_id=str(self.user.pk),
            provider=self.provider,
            provider_session_id=self.provider_session_id,
            status=self.status,
            verification_type=self.verification_type,
            client_secret=self.client_secret,
            metadata=self.metadata,
            verification_report_id=self.verification_report_id,
            verified_at=self.verified_at,
            verified_first_name=self.verified_first_name,
            verified_last_name=self.verified_last_name,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class KYCStatusMixin(models.Model):
    """
    Simple KYC status mixin for User models.

    Add this directly to your User model:

        from swap_layer.identity.verification.models import KYCStatusMixin

        class User(KYCStatusMixin, AbstractUser):
            # ... your fields
    """

    kyc_status = models.CharField(
        max_length=50,
        default="not_started",
        choices=[
            ("not_started", "Not Started"),
            ("pending", "Pending"),
            ("verified", "Verified"),
            ("failed", "Failed"),
        ],
        help_text="Overall KYC verification status",
    )
    kyc_verified_at = models.DateTimeField(blank=True, null=True, help_text="When KYC was verified")
    kyc_required = models.BooleanField(
        default=False, help_text="Whether KYC is required for this user"
    )

    class Meta:
        abstract = True
