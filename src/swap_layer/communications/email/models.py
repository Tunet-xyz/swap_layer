"""
Django model mixins for storing email provider metadata.

These mixins help you track email sending and store provider-specific data
in your Django models while maintaining vendor independence.
"""

from django.db import models


class EmailLogMixin(models.Model):
    """
    Mixin for logging sent emails.

    Add this to your EmailLog model:

        from swap_layer.email.models import EmailLogMixin

        class EmailLog(EmailLogMixin, models.Model):
            user = models.ForeignKey(User, on_delete=models.CASCADE)
            # ... your fields
    """

    email_provider = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ("smtp", "SMTP"),
            ("sendgrid", "SendGrid"),
            ("mailgun", "Mailgun"),
            ("ses", "AWS SES"),
            ("django", "Django Anymail"),
        ],
        help_text="Email provider used",
    )
    email_message_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text="Message ID from email provider",
    )
    to_email = models.EmailField(help_text="Recipient email address")
    from_email = models.EmailField(help_text="Sender email address")
    subject = models.CharField(max_length=255, help_text="Email subject line")
    status = models.CharField(
        max_length=50,
        default="sent",
        choices=[
            ("sent", "Sent"),
            ("delivered", "Delivered"),
            ("opened", "Opened"),
            ("clicked", "Clicked"),
            ("bounced", "Bounced"),
            ("failed", "Failed"),
        ],
        help_text="Email delivery status",
    )
    sent_at = models.DateTimeField(auto_now_add=True, help_text="When the email was sent")
    delivered_at = models.DateTimeField(
        blank=True, null=True, help_text="When the email was delivered"
    )
    opened_at = models.DateTimeField(
        blank=True, null=True, help_text="When the email was first opened"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["email_provider", "email_message_id"]),
            models.Index(fields=["to_email"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-sent_at"]),
        ]


class EmailSuppressionMixin(models.Model):
    """
    Mixin for tracking email suppressions (bounces, complaints).

    Add this to your EmailSuppression model:

        from swap_layer.email.models import EmailSuppressionMixin

        class EmailSuppression(EmailSuppressionMixin, models.Model):
            # ... your fields
    """

    email_address = models.EmailField(
        unique=True, db_index=True, help_text="Suppressed email address"
    )
    suppression_type = models.CharField(
        max_length=50,
        choices=[
            ("bounce", "Bounce"),
            ("complaint", "Complaint"),
            ("unsubscribe", "Unsubscribe"),
            ("manual", "Manual"),
        ],
        help_text="Type of suppression",
    )
    reason = models.TextField(blank=True, null=True, help_text="Reason for suppression")
    suppressed_at = models.DateTimeField(
        auto_now_add=True, help_text="When the email was suppressed"
    )
    provider = models.CharField(
        max_length=50, blank=True, null=True, help_text="Provider that reported the suppression"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["suppression_type"]),
            models.Index(fields=["-suppressed_at"]),
        ]
