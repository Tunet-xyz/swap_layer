"""
Django Admin integration for identity platform provider models.

Add this to your admin.py:

    from swap_layer.identity.platform.admin import OAuthIdentityAdminMixin

    @admin.register(UserIdentity)
    class UserIdentityAdmin(OAuthIdentityAdminMixin, admin.ModelAdmin):
        list_display = ['user', 'identity_provider', 'provider_email', 'last_login_at']
"""

from django.contrib import admin
from django.utils.html import format_html


class OAuthIdentityAdminMixin:
    """
    Admin mixin for models using OAuthIdentityMixin.

    Adds helpful fields for OAuth identity management.
    """

    @admin.display(description="Provider", ordering="identity_provider")
    def provider_badge(self, obj):
        """Display identity provider badge."""
        if not obj.identity_provider:
            return format_html('<span style="color: #999;">{}</span>', "—")

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

    @admin.display(description="Token", ordering="provider_token_expires_at")
    def token_status(self, obj):
        """Display token expiration status."""
        if not obj.provider_token_expires_at:
            return format_html('<span style="color: #999;">{}</span>', "No token")

        from django.utils import timezone

        now = timezone.now()

        if obj.provider_token_expires_at > now:
            return format_html('<span style="color: #28a745;">{}</span>', "✓ Valid")
        else:
            return format_html('<span style="color: #dc3545;">{}</span>', "✗ Expired")


class SSOConnectionAdminMixin:
    """
    Admin mixin for models using SSOConnectionMixin.

    Adds helpful fields for SSO connection management.
    """

    @admin.display(description="SSO Status", ordering="sso_enabled")
    def sso_status_badge(self, obj):
        """Display SSO enabled status."""
        if obj.sso_enabled:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
                "ENABLED",
            )
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            "DISABLED",
        )

    @admin.display(description="SSO Provider")
    def sso_provider_link(self, obj):
        """Display SSO provider with link to dashboard."""
        if not obj.sso_provider or not obj.sso_connection_id:
            return format_html('<span style="color: #999;">{}</span>', "—")

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
