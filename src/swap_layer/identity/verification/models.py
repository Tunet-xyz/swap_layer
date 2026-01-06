"""
Django model mixins for storing identity verification provider metadata.

These mixins help you track KYC/identity verification sessions and results
while maintaining provider independence.
"""

from django.db import models
from django.utils import timezone


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
            ('stripe', 'Stripe Identity'),
            ('onfido', 'Onfido'),
        ],
        help_text="Identity verification provider"
    )
    verification_session_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Session ID from verification provider"
    )
    verification_status = models.CharField(
        max_length=50,
        default='requires_input',
        choices=[
            ('requires_input', 'Requires Input'),
            ('processing', 'Processing'),
            ('verified', 'Verified'),
            ('canceled', 'Canceled'),
        ],
        help_text="Current verification status"
    )
    verification_type = models.CharField(
        max_length=50,
        default='document',
        choices=[
            ('document', 'Document'),
            ('id_number', 'ID Number'),
        ],
        help_text="Type of verification"
    )
    client_secret = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Client secret for frontend integration"
    )
    verification_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL for user to complete verification"
    )
    
    # Verified data fields
    verified_first_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="First name from verified document"
    )
    verified_last_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Last name from verified document"
    )
    verified_date_of_birth = models.DateField(
        blank=True,
        null=True,
        help_text="Date of birth from verified document"
    )
    verified_address_line1 = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Address line 1 from verified document"
    )
    verified_address_city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="City from verified document"
    )
    verified_address_postal_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Postal code from verified document"
    )
    verified_address_country = models.CharField(
        max_length=2,
        blank=True,
        null=True,
        help_text="Country code from verified document"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When verification session was created"
    )
    verified_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When verification was completed"
    )
    
    # Metadata
    verification_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional verification data from provider"
    )
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['verification_provider', 'verification_session_id']),
            models.Index(fields=['verification_status']),
            models.Index(fields=['-created_at']),
        ]


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
        default='not_started',
        choices=[
            ('not_started', 'Not Started'),
            ('pending', 'Pending'),
            ('verified', 'Verified'),
            ('failed', 'Failed'),
        ],
        help_text="Overall KYC verification status"
    )
    kyc_verified_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When KYC was verified"
    )
    kyc_required = models.BooleanField(
        default=False,
        help_text="Whether KYC is required for this user"
    )
    
    class Meta:
        abstract = True

