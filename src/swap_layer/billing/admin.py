"""
Django Admin integration for payment provider models.

Add this to your admin.py:

    from swap_layer.billing.admin import PaymentProviderAdminMixin

    @admin.register(Customer)
    class CustomerAdmin(PaymentProviderAdminMixin, admin.ModelAdmin):
        list_display = ['email', 'name', 'payment_provider', 'payment_customer_id']
"""

from django.utils.html import format_html


class PaymentProviderAdminMixin:
    """
    Admin mixin for models using payment provider mixins.

    Adds helpful fields and actions for payment management.
    """

    def payment_provider_link(self, obj):
        """Display payment provider with link to dashboard."""
        if not obj.payment_provider or not obj.payment_customer_id:
            return format_html('<span style="color: #999;">—</span>')

        dashboard_urls = {
            "stripe": f"https://dashboard.stripe.com/customers/{obj.payment_customer_id}",
            "paypal": f"https://www.paypal.com/billing/customers/{obj.payment_customer_id}",
        }

        url = dashboard_urls.get(obj.payment_provider)
        if url:
            return format_html(
                '<a href="{}" target="_blank">{} <span style="color: #999;">↗</span></a>',
                url,
                obj.payment_customer_id,
            )
        return obj.payment_customer_id

    payment_provider_link.short_description = "Provider ID"

    def has_payment_customer(self, obj):
        """Check if customer exists in payment provider."""
        return bool(obj.payment_customer_id)

    has_payment_customer.boolean = True
    has_payment_customer.short_description = "Has Payment Customer"


class SubscriptionAdminMixin:
    """
    Admin mixin for subscription models.

    Adds subscription-specific fields and actions.
    """

    def subscription_link(self, obj):
        """Display subscription with link to provider dashboard."""
        if not obj.subscription_provider or not obj.subscription_id:
            return format_html('<span style="color: #999;">—</span>')

        dashboard_urls = {
            "stripe": f"https://dashboard.stripe.com/subscriptions/{obj.subscription_id}",
        }

        url = dashboard_urls.get(obj.subscription_provider)
        if url:
            return format_html(
                '<a href="{}" target="_blank">{} <span style="color: #999;">↗</span></a>',
                url,
                obj.subscription_id,
            )
        return obj.subscription_id

    subscription_link.short_description = "Subscription ID"

    def subscription_status_badge(self, obj):
        """Display subscription status with color badge."""
        if not obj.subscription_status:
            return format_html('<span style="color: #999;">—</span>')

        colors = {
            "active": "#28a745",
            "past_due": "#ffc107",
            "canceled": "#dc3545",
            "incomplete": "#6c757d",
            "trialing": "#17a2b8",
        }

        color = colors.get(obj.subscription_status, "#6c757d")
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.subscription_status.upper(),
        )

    subscription_status_badge.short_description = "Status"
