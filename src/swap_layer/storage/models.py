"""
Django model mixins for storing file storage metadata.

These mixins help you track uploaded files and store provider-specific data
in your Django models while maintaining vendor independence.
"""

from django.db import models


class StorageFileMixin(models.Model):
    """
    Mixin for tracking uploaded files.

    Add this to your UploadedFile model:

        from swap_layer.storage.models import StorageFileMixin

        class UploadedFile(StorageFileMixin, models.Model):
            user = models.ForeignKey(User, on_delete=models.CASCADE)
            # ... your fields
    """

    storage_provider = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ("local", "Local Storage"),
            ("s3", "AWS S3"),
            ("azure", "Azure Blob"),
            ("gcs", "Google Cloud Storage"),
            ("django", "Django Storage"),
        ],
        help_text="Storage provider used",
    )
    file_key = models.CharField(max_length=255, db_index=True, help_text="File path/key in storage")
    original_filename = models.CharField(max_length=255, help_text="Original filename from upload")
    file_size = models.BigIntegerField(help_text="File size in bytes")
    content_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="MIME type (image/jpeg, application/pdf, etc.)",
    )
    file_url = models.URLField(
        max_length=500, blank=True, null=True, help_text="Public URL to access the file"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, help_text="When the file was uploaded")
    is_public = models.BooleanField(
        default=False, help_text="Whether the file is publicly accessible"
    )
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Additional metadata (dimensions, duration, etc.)"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["storage_provider", "file_key"]),
            models.Index(fields=["content_type"]),
            models.Index(fields=["-uploaded_at"]),
        ]


class StorageQuotaMixin(models.Model):
    """
    Mixin for tracking storage quota usage.

    Add this to your User or Account model:

        from swap_layer.storage.models import StorageQuotaMixin

        class Account(StorageQuotaMixin, models.Model):
            # ... your fields
    """

    storage_quota_bytes = models.BigIntegerField(
        default=1073741824,  # 1 GB default
        help_text="Total storage quota in bytes",
    )
    storage_used_bytes = models.BigIntegerField(
        default=0, help_text="Storage currently used in bytes"
    )
    storage_files_count = models.IntegerField(default=0, help_text="Number of files stored")
    storage_last_checked_at = models.DateTimeField(
        blank=True, null=True, help_text="When storage usage was last calculated"
    )

    class Meta:
        abstract = True

    def storage_usage_percentage(self):
        """Calculate percentage of quota used."""
        if self.storage_quota_bytes == 0:
            return 0
        return (self.storage_used_bytes / self.storage_quota_bytes) * 100

    def storage_available_bytes(self):
        """Calculate remaining storage in bytes."""
        return max(0, self.storage_quota_bytes - self.storage_used_bytes)

    def is_storage_quota_exceeded(self):
        """Check if quota is exceeded."""
        return self.storage_used_bytes >= self.storage_quota_bytes
