"""
Django Admin integration for SMS provider models.

Add this to your admin.py:

    from swap_layer.communications.sms.admin import SMSMessageAdminMixin

    @admin.register(SMSMessage)
    class SMSMessageAdmin(SMSMessageAdminMixin, admin.ModelAdmin):
        list_display = ['to_phone', 'status', 'sms_provider', 'sent_at']
"""

from django.contrib import admin
from django.utils.html import format_html


class SMSMessageAdminMixin:
    """
    Admin mixin for models using SMSMessageMixin.

    Adds helpful fields and actions for SMS tracking.
    """

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        """Display SMS status with color badge."""
        if not obj.status:
            return format_html('<span style="color: #999;">{}</span>', "—")

        colors = {
            "queued": "#6c757d",
            "sent": "#17a2b8",
            "delivered": "#28a745",
            "failed": "#dc3545",
            "undelivered": "#dc3545",
        }

        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.status.upper(),
        )

    @admin.display(description="Provider", ordering="sms_provider")
    def provider_link(self, obj):
        """Display provider with link to dashboard."""
        if not obj.sms_provider or not obj.sms_message_id:
            return format_html('<span style="color: #999;">{}</span>', "—")

        dashboard_urls = {
            "twilio": f"https://console.twilio.com/monitor/logs/sms/{obj.sms_message_id}",
        }

        url = dashboard_urls.get(obj.sms_provider)
        if url:
            return format_html(
                '<a href="{}" target="_blank">{} <span style="color: #999;">↗</span></a>',
                url,
                obj.sms_provider.upper(),
            )
        return obj.sms_provider.upper() if obj.sms_provider else "—"

    @admin.display(description="Message")
    def message_preview(self, obj):
        """Display truncated message preview."""
        if not obj.message_body:
            return format_html('<span style="color: #999;">{}</span>', "—")

        preview = obj.message_body[:50]
        if len(obj.message_body) > 50:
            preview += "..."
        return preview


class SMSPhoneNumberAdminMixin:
    """
    Admin mixin for models using SMSPhoneNumberMixin.

    Adds helpful fields for phone number management.
    """

    @admin.display(description="Status", ordering="is_verified")
    def verification_status(self, obj):
        """Display verification status."""
        if obj.is_verified:
            return format_html('<span style="color: #28a745;">{}</span>', "✓ Verified")
        return format_html('<span style="color: #6c757d;">{}</span>', "Not Verified")
