"""
Django Admin integration for storage provider models.

Add this to your admin.py:

    from swap_layer.storage.admin import StorageFileAdminMixin

    @admin.register(UploadedFile)
    class UploadedFileAdmin(StorageFileAdminMixin, admin.ModelAdmin):
        list_display = ['original_filename', 'file_size_display', 'content_type', 'storage_provider', 'uploaded_at']
"""

from django.utils.html import format_html


class StorageFileAdminMixin:
    """
    Admin mixin for models using StorageFileMixin.

    Adds helpful fields and actions for file management.
    """

    def file_size_display(self, obj):
        """Display file size in human-readable format."""
        if not obj.file_size:
            return format_html('<span style="color: #999;">—</span>')

        size = obj.file_size
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        return f"{size:.2f} {units[unit_index]}"

    file_size_display.short_description = "Size"
    file_size_display.admin_order_field = "file_size"

    def file_preview(self, obj):
        """Display file preview for images."""
        if not obj.content_type or not obj.content_type.startswith("image/"):
            return format_html('<span style="color: #999;">—</span>')

        if obj.file_url:
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width: 50px; max-height: 50px; object-fit: cover;" /></a>',
                obj.file_url,
                obj.file_url,
            )
        return format_html('<span style="color: #999;">No preview</span>')

    file_preview.short_description = "Preview"

    def file_link(self, obj):
        """Display link to file."""
        if not obj.file_url:
            return format_html('<span style="color: #999;">—</span>')

        return format_html(
            '<a href="{}" target="_blank">Open <span style="color: #999;">↗</span></a>',
            obj.file_url,
        )

    file_link.short_description = "Link"

    def provider_badge(self, obj):
        """Display storage provider badge."""
        if not obj.storage_provider:
            return format_html('<span style="color: #999;">—</span>')

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

    provider_badge.short_description = "Provider"
    provider_badge.admin_order_field = "storage_provider"


class StorageQuotaAdminMixin:
    """
    Admin mixin for models using StorageQuotaMixin.

    Adds helpful fields for quota management.
    """

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
            '<div style="width: 150px; background: #e9ecef; border-radius: 4px; overflow: hidden;">'
            '<div style="width: {:.1f}%; background: {}; height: 20px; display: flex; align-items: center; justify-content: center; color: white; font-size: 11px;">'
            "{:.1f}%"
            "</div>"
            "</div>",
            min(percentage, 100),
            color,
            percentage,
        )

    quota_usage_bar.short_description = "Quota Usage"

    def storage_info(self, obj):
        """Display storage usage info."""
        used_gb = obj.storage_used_bytes / (1024**3)
        total_gb = obj.storage_quota_bytes / (1024**3)

        return format_html(
            "<span>{:.2f} GB / {:.2f} GB</span><br>"
            '<span style="color: #6c757d; font-size: 11px;">{} files</span>',
            used_gb,
            total_gb,
            obj.storage_files_count,
        )

    storage_info.short_description = "Storage"
