"""
Django model mixins for storing payment provider metadata.

These mixins help you persist provider-specific data in your Django models
while maintaining vendor independence.
"""

from django.db import models


class StripeCustomerMixin(models.Model):
    """
    Mixin for storing Stripe customer metadata.

    Add this to your User or Customer model:

        from swap_layer.billing.models import StripeCustomerMixin

        class Customer(StripeCustomerMixin, models.Model):
            email = models.EmailField()
            # ... your fields
    """

    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        help_text="Stripe customer ID (cus_...)",
    )
    stripe_customer_created_at = models.DateTimeField(
        blank=True, null=True, help_text="When the Stripe customer was created"
    )

    class Meta:
        abstract = True


class PaymentProviderCustomerMixin(models.Model):
    """
    Generic mixin for storing payment provider customer IDs.

    Use this if you want to support multiple payment providers:

        from swap_layer.billing.models import PaymentProviderCustomerMixin

        class Customer(PaymentProviderCustomerMixin, models.Model):
            email = models.EmailField()
            # ... your fields

    Then store IDs like:
        customer.payment_provider = 'stripe'
        customer.payment_customer_id = 'cus_...'
    """

    payment_provider = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ("stripe", "Stripe"),
            ("paypal", "PayPal"),
            ("square", "Square"),
        ],
        help_text="Which payment provider is used",
    )
    payment_customer_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text="Customer ID from payment provider",
    )
    payment_customer_created_at = models.DateTimeField(
        blank=True, null=True, help_text="When the payment customer was created"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["payment_provider", "payment_customer_id"]),
        ]


class SubscriptionMixin(models.Model):
    """
    Mixin for storing subscription metadata.

    Add this to your Subscription model:

        from swap_layer.billing.models import SubscriptionMixin

        class Subscription(SubscriptionMixin, models.Model):
            user = models.ForeignKey(User, on_delete=models.CASCADE)
            plan = models.CharField(max_length=100)
            # ... your fields
    """

    subscription_provider = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ("stripe", "Stripe"),
            ("paypal", "PayPal"),
        ],
        help_text="Payment provider for this subscription",
    )
    subscription_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text="Subscription ID from provider (sub_...)",
    )
    subscription_status = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ("active", "Active"),
            ("past_due", "Past Due"),
            ("canceled", "Canceled"),
            ("incomplete", "Incomplete"),
            ("trialing", "Trialing"),
        ],
        help_text="Current subscription status",
    )
    subscription_current_period_start = models.DateTimeField(
        blank=True, null=True, help_text="Start of current billing period"
    )
    subscription_current_period_end = models.DateTimeField(
        blank=True, null=True, help_text="End of current billing period"
    )
    subscription_cancel_at_period_end = models.BooleanField(
        default=False, help_text="Whether subscription cancels at period end"
    )

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["subscription_provider", "subscription_id"]),
            models.Index(fields=["subscription_status"]),
        ]


class PaymentMethodMixin(models.Model):
    """
    Mixin for storing payment method metadata.

    Add this to your PaymentMethod model:

        from swap_layer.billing.models import PaymentMethodMixin

        class PaymentMethod(PaymentMethodMixin, models.Model):
            customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
            # ... your fields
    """

    payment_method_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        help_text="Payment method ID from provider (pm_...)",
    )
    payment_method_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ("card", "Credit/Debit Card"),
            ("bank_account", "Bank Account"),
            ("paypal", "PayPal"),
        ],
        help_text="Type of payment method",
    )
    payment_method_last4 = models.CharField(
        max_length=4, blank=True, null=True, help_text="Last 4 digits of card/account"
    )
    payment_method_brand = models.CharField(
        max_length=50, blank=True, null=True, help_text="Card brand (visa, mastercard, etc.)"
    )
    payment_method_exp_month = models.IntegerField(
        blank=True, null=True, help_text="Card expiration month"
    )
    payment_method_exp_year = models.IntegerField(
        blank=True, null=True, help_text="Card expiration year"
    )
    is_default = models.BooleanField(default=False, help_text="Is this the default payment method")

    class Meta:
        abstract = True
