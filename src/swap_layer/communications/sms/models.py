"""
Django model mixins for storing SMS provider metadata.

These mixins help you track SMS messages and store provider-specific data
in your Django models while maintaining vendor independence.
"""

from django.db import models


class SMSMessageMixin(models.Model):
    """
    Mixin for logging sent SMS messages.

    Add this to your SMSMessage model:

        from swap_layer.sms.models import SMSMessageMixin

        class SMSMessage(SMSMessageMixin, models.Model):
            user = models.ForeignKey(User, on_delete=models.CASCADE)
            # ... your fields
    """

    sms_provider = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ("twilio", "Twilio"),
            ("sns", "AWS SNS"),
        ],
        help_text="SMS provider used",
    )
    sms_message_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text="Message ID from SMS provider (SID for Twilio)",
    )
    to_phone = models.CharField(max_length=20, help_text="Recipient phone number (E.164 format)")
    from_phone = models.CharField(
        max_length=20, blank=True, null=True, help_text="Sender phone number"
    )
    message_body = models.TextField(help_text="SMS message content")
    status = models.CharField(
        max_length=50,
        default="sent",
        choices=[
            ("queued", "Queued"),
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("failed", "Failed"),
            ("undelivered", "Undelivered"),
        ],
        help_text="Message delivery status",
    )
    sent_at = models.DateTimeField(auto_now_add=True, help_text="When the SMS was sent")
    delivered_at = models.DateTimeField(
        blank=True, null=True, help_text="When the SMS was delivered"
    )
    error_message = models.TextField(
        blank=True, null=True, help_text="Error message if delivery failed"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["sms_provider", "sms_message_id"]),
            models.Index(fields=["to_phone"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-sent_at"]),
        ]


class SMSPhoneNumberMixin(models.Model):
    """
    Mixin for storing phone numbers with validation status.

    Add this to your PhoneNumber model:

        from swap_layer.sms.models import SMSPhoneNumberMixin

        class PhoneNumber(SMSPhoneNumberMixin, models.Model):
            user = models.OneToOneField(User, on_delete=models.CASCADE)
            # ... your fields
    """

    phone_number = models.CharField(
        max_length=20, db_index=True, help_text="Phone number in E.164 format (+1234567890)"
    )
    is_verified = models.BooleanField(
        default=False, help_text="Whether the phone number has been verified"
    )
    verification_code = models.CharField(
        max_length=10, blank=True, null=True, help_text="Temporary verification code"
    )
    verification_code_expires_at = models.DateTimeField(
        blank=True, null=True, help_text="When the verification code expires"
    )
    verified_at = models.DateTimeField(
        blank=True, null=True, help_text="When the phone number was verified"
    )
    carrier_name = models.CharField(
        max_length=100, blank=True, null=True, help_text="Phone carrier name (from lookup)"
    )
    country_code = models.CharField(
        max_length=2, blank=True, null=True, help_text="ISO country code (US, GB, etc.)"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["phone_number"]),
            models.Index(fields=["is_verified"]),
        ]
