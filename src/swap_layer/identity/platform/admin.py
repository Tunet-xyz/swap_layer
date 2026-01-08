"""
Django Admin integration for identity platform provider models.

Add this to your admin.py:

    from swap_layer.identity.platform.admin import OAuthIdentityAdminMixin

    @admin.register(UserIdentity)
    class UserIdentityAdmin(OAuthIdentityAdminMixin, admin.ModelAdmin):
        list_display = ['user', 'identity_provider', 'provider_email', 'last_login_at']
"""

from django.utils.html import format_html


class OAuthIdentityAdminMixin:
    """
    Admin mixin for models using OAuthIdentityMixin.

    Adds helpful fields for OAuth identity management.
    """

    def provider_badge(self, obj):
        """Display identity provider badge."""
        if not obj.identity_provider:
            return format_html('<span style="color: #999;">—</span>')

        provider_colors = {
            "workos": "#6363f1",
            "auth0": "#eb5424",
        }

        color = provider_colors.get(obj.identity_provider, "#6c757d")
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.identity_provider.upper(),
        )

    provider_badge.short_description = "Provider"
    provider_badge.admin_order_field = "identity_provider"

    def token_status(self, obj):
        """Display token expiration status."""
        if not obj.provider_token_expires_at:
            return format_html('<span style="color: #999;">No token</span>')

        from django.utils import timezone

        now = timezone.now()

        if obj.provider_token_expires_at > now:
            return format_html('<span style="color: #28a745;">✓ Valid</span>')
        else:
            return format_html('<span style="color: #dc3545;">✗ Expired</span>')

    token_status.short_description = "Token"
    token_status.admin_order_field = "provider_token_expires_at"


class SSOConnectionAdminMixin:
    """
    Admin mixin for models using SSOConnectionMixin.

    Adds helpful fields for SSO connection management.
    """

    def sso_status_badge(self, obj):
        """Display SSO enabled status."""
        if obj.sso_enabled:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">ENABLED</span>'
            )
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">DISABLED</span>'
        )

    sso_status_badge.short_description = "SSO Status"
    sso_status_badge.admin_order_field = "sso_enabled"

    def sso_provider_link(self, obj):
        """Display SSO provider with link to dashboard."""
        if not obj.sso_provider or not obj.sso_connection_id:
            return format_html('<span style="color: #999;">—</span>')

        dashboard_urls = {
            "workos": f"https://dashboard.workos.com/connections/{obj.sso_connection_id}",
            "auth0": "https://manage.auth0.com/dashboard/",
        }

        url = dashboard_urls.get(obj.sso_provider)
        if url:
            return format_html(
                '<a href="{}" target="_blank">{} <span style="color: #999;">↗</span></a>',
                url,
                obj.sso_provider.upper(),
            )
        return obj.sso_provider.upper() if obj.sso_provider else "—"

    sso_provider_link.short_description = "SSO Provider"
