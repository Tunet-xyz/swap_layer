"""
Django Admin integration for storage provider models.

Add this to your admin.py:

    from swap_layer.storage.admin import StorageFileAdminMixin

    @admin.register(UploadedFile)
    class UploadedFileAdmin(StorageFileAdminMixin, admin.ModelAdmin):
        list_display = ['original_filename', 'file_size_display', 'content_type', 'storage_provider', 'uploaded_at']
"""

from django.contrib import admin
from django.utils.html import format_html


class StorageFileAdminMixin:
    """
    Admin mixin for models using StorageFileMixin.

    Adds helpful fields and actions for file management.
    """

    @admin.display(description="Size", ordering="file_size")
    def file_size_display(self, obj):
        """Display file size in human-readable format."""
        if not obj.file_size:
            return format_html('<span style="color: #999;">{}</span>', "—")

        size = obj.file_size
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.2f} {units[unit_index]}"

    @admin.display(description="Preview")
    def file_preview(self, obj):
        """Display file preview for images."""
        if not obj.content_type or not obj.content_type.startswith("image/"):
            return format_html('<span style="color: #999;">{}</span>', "—")

        if obj.file_url:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 50px; max-height: 50px; object-fit: cover;" /></a>',
                obj.file_url,
                obj.file_url,
            )
        return format_html('<span style="color: #999;">{}</span>', "No preview")

    @admin.display(description="Link")
    def file_link(self, obj):
        """Display link to file."""
        if not obj.file_url:
            return format_html('<span style="color: #999;">{}</span>', "—")

        return format_html(
            '<a href="{}" target="_blank">Open <span style="color: #999;">↗</span></a>',
            obj.file_url,
        )

    @admin.display(description="Provider", ordering="storage_provider")
    def provider_badge(self, obj):
        """Display storage provider badge."""
        if not obj.storage_provider:
            return format_html('<span style="color: #999;">{}</span>', "—")

        provider_colors = {
            "local": "#6c757d",
            "s3": "#ff9900",
            "azure": "#0078d4",
            "gcs": "#4285f4",
            "django": "#092e20",
        }

        color = provider_colors.get(obj.storage_provider, "#6c757d")
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.storage_provider.upper(),
        )


class StorageQuotaAdminMixin:
    """
    Admin mixin for models using StorageQuotaMixin.

    Adds helpful fields for quota management.
    """

    @admin.display(description="Quota Usage")
    def quota_usage_bar(self, obj):
        """Display quota usage as progress bar."""
        percentage = obj.storage_usage_percentage()

        if percentage >= 90:
            color = "#dc3545"  # Red
        elif percentage >= 75:
            color = "#ffc107"  # Yellow
        else:
            color = "#28a745"  # Green

        return format_html(
            '<div style="width: 150px; background: #e9ecef; border-radius: 4px; overflow: hidden; position: relative;">'
            '<div style="width: {}%; background: {}; height: 20px;"></div>'
            '<span style="position: absolute; inset: 0; text-align: center; color: #111; font-size: 11px;">{}%</span>'
            "</div>",
            f"{min(percentage, 100):.1f}",
            color,
            f"{percentage:.1f}",
        )

    @admin.display(description="Storage")
    def storage_info(self, obj):
        """Display storage usage info."""
        used_gb = obj.storage_used_bytes / (1024**3)
        total_gb = obj.storage_quota_bytes / (1024**3)

        return format_html(
            "<span>{} GB / {} GB</span><br>"
            '<span style="color: #6c757d; font-size: 11px;">{} files</span>',
            f"{used_gb:.2f}",
            f"{total_gb:.2f}",
            obj.storage_files_count,
        )
