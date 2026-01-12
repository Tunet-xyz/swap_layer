"""
Django Admin integration for email provider models.

Add this to your admin.py:

    from swap_layer.email.admin import EmailLogAdminMixin

    @admin.register(EmailLog)
    class EmailLogAdmin(EmailLogAdminMixin, admin.ModelAdmin):
        list_display = ['to_email', 'subject', 'status', 'email_provider', 'sent_at']
"""

from django.utils.html import format_html


class EmailLogAdminMixin:
    """
    Admin mixin for models using EmailLogMixin.

    Adds helpful fields and actions for email tracking.
    """

    def status_badge(self, obj):
        """Display email status with color badge."""
        if not obj.status:
            return format_html('<span style="color: #999;">—</span>')

        colors = {
            "sent": "#17a2b8",
            "delivered": "#28a745",
            "opened": "#007bff",
            "clicked": "#6f42c1",
            "bounced": "#dc3545",
            "failed": "#dc3545",
        }

        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.status.upper(),
        )

    status_badge.short_description = "Status"
    status_badge.admin_order_field = "status"

    def provider_badge(self, obj):
        """Display provider with badge."""
        if not obj.email_provider:
            return format_html('<span style="color: #999;">—</span>')

        return format_html(
            '<span style="background: #6c757d; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            obj.email_provider.upper(),
        )

    provider_badge.short_description = "Provider"
    provider_badge.admin_order_field = "email_provider"


class EmailSuppressionAdminMixin:
    """
    Admin mixin for models using EmailSuppressionMixin.

    Adds helpful fields for suppression management.
    """

    def suppression_type_badge(self, obj):
        """Display suppression type with color badge."""
        if not obj.suppression_type:
            return format_html('<span style="color: #999;">—</span>')

        colors = {
            "bounce": "#dc3545",
            "complaint": "#ffc107",
            "unsubscribe": "#17a2b8",
            "manual": "#6c757d",
        }

        color = colors.get(obj.suppression_type, "#6c757d")
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.suppression_type.upper(),
        )

    suppression_type_badge.short_description = "Type"
    suppression_type_badge.admin_order_field = "suppression_type"
