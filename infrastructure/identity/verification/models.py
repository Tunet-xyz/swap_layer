from django.db import models
from django.conf import settings
from django.utils import timezone

class IdentityVerificationSession(models.Model):
    """
    Stores identity verification session data.
    """
    
    STATUS_CHOICES = [
        ('requires_input', 'Requires Input'),
        ('processing', 'Processing'),
        ('verified', 'Verified'),
        ('canceled', 'Canceled'),
        ('failed', 'Failed'),
    ]
    
    TYPE_CHOICES = [
        ('document', 'Document Verification'),
        ('id_number', 'ID Number Verification'),
    ]

    PROVIDER_CHOICES = [
        ('stripe', 'Stripe'),
        # Add other providers here
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='identity_verifications'
    )
    provider = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        default='stripe'
    )
    provider_session_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Session ID from the identity provider"
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='requires_input',
        db_index=True
    )
    verification_type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        default='document'
    )
    client_secret = models.CharField(
        max_length=255,
        blank=True,
        help_text="Client secret for frontend integration"
    )
    verification_report_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="ID of the verification report"
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the verification was completed"
    )
    created_at = models.DateTimeField(
        default=timezone.now
    )
    updated_at = models.DateTimeField(
        auto_now=True
    )
    
    # Verified outputs (stored as JSON-like fields)
    verified_first_name = models.CharField(max_length=255, blank=True)
    verified_last_name = models.CharField(max_length=255, blank=True)
    verified_dob = models.DateField(null=True, blank=True)
    verified_address_line1 = models.CharField(max_length=255, blank=True)
    verified_address_city = models.CharField(max_length=255, blank=True)
    verified_address_postal_code = models.CharField(max_length=50, blank=True)
    verified_address_country = models.CharField(max_length=2, blank=True)
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Identity Verification Session'
        verbose_name_plural = 'Identity Verification Sessions'

    def __str__(self):
        return f"{self.user.username} - {self.provider} - {self.status}"
