"""
Django Admin integration for identity verification provider models.

Add this to your admin.py:

    from swap_layer.identity.verification.admin import IdentityVerificationAdminMixin

    @admin.register(IdentityVerification)
    class IdentityVerificationAdmin(IdentityVerificationAdminMixin, admin.ModelAdmin):
        list_display = ['user', 'verification_status', 'verification_provider', 'created_at']
"""

from django.contrib import admin
from django.utils.html import format_html


class IdentityVerificationAdminMixin:
    """
    Admin mixin for models using IdentityVerificationMixin.

    Adds helpful fields for identity verification tracking.
    """

    @admin.display(description="Status", ordering="verification_status")
    def verification_status_badge(self, obj):
        """Display verification status with color badge."""
        if not obj.verification_status:
            return format_html('<span style="color: #999;">{}</span>', "—")

        colors = {
            "requires_input": "#6c757d",
            "processing": "#ffc107",
            "verified": "#28a745",
            "canceled": "#dc3545",
        }

        color = colors.get(obj.verification_status, "#6c757d")
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.verification_status.upper().replace("_", " "),
        )

    @admin.display(description="Provider", ordering="verification_provider")
    def provider_link(self, obj):
        """Display provider with link to dashboard."""
        if not obj.verification_provider or not obj.verification_session_id:
            return format_html('<span style="color: #999;">{}</span>', "—")

        dashboard_urls = {
            "stripe": f"https://dashboard.stripe.com/identity/verification_sessions/{obj.verification_session_id}",
        }

        url = dashboard_urls.get(obj.verification_provider)
        if url:
            return format_html(
                '<a href="{}" target="_blank">{} <span style="color: #999;">↗</span></a>',
                url,
                obj.verification_provider.upper(),
            )
        return obj.verification_provider.upper() if obj.verification_provider else "—"

    @admin.display(description="Verified Name")
    def verified_name(self, obj):
        """Display verified name if available."""
        if obj.verified_first_name or obj.verified_last_name:
            first = obj.verified_first_name or ""
            last = obj.verified_last_name or ""
            return f"{first} {last}".strip()
        return format_html('<span style="color: #999;">{}</span>', "—")


class KYCStatusAdminMixin:
    """
    Admin mixin for models using KYCStatusMixin.

    Adds helpful fields for KYC status display.
    """

    @admin.display(description="KYC Status", ordering="kyc_status")
    def kyc_status_badge(self, obj):
        """Display KYC status with color badge."""
        if not obj.kyc_status:
            return format_html('<span style="color: #999;">{}</span>', "—")

        colors = {
            "not_started": "#6c757d",
            "pending": "#ffc107",
            "verified": "#28a745",
            "failed": "#dc3545",
        }

        color = colors.get(obj.kyc_status, "#6c757d")
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.kyc_status.upper().replace("_", " "),
        )

    @admin.display(description="KYC Required", ordering="kyc_required")
    def kyc_required_icon(self, obj):
        """Display KYC required icon."""
        if obj.kyc_required:
            return format_html('<span style="color: #dc3545;">{}</span>', "✓ Required")
        return format_html('<span style="color: #999;">{}</span>', "Not Required")
