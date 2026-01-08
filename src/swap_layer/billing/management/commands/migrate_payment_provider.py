"""
Django management command to migrate payment providers.

This command helps you migrate from one payment provider to another
by creating equivalent customers and subscriptions in the new provider.

Usage:
    python manage.py migrate_payment_provider stripe paypal --dry-run
    python manage.py migrate_payment_provider stripe paypal --confirm
"""

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Migrate customers and subscriptions from one payment provider to another"

    def add_arguments(self, parser):
        parser.add_argument("from_provider", type=str, help='Current provider (e.g., "stripe")')
        parser.add_argument("to_provider", type=str, help='Target provider (e.g., "paypal")')
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be migrated without making changes",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually perform the migration (required)",
        )
        parser.add_argument(
            "--model",
            type=str,
            default="auth.User",
            help="Model containing customer data (default: auth.User)",
        )

    def handle(self, *args, **options):
        from_provider = options["from_provider"]
        to_provider = options["to_provider"]
        dry_run = options["dry_run"]
        confirm = options["confirm"]
        model_path = options["model"]

        if not dry_run and not confirm:
            raise CommandError(
                "You must specify either --dry-run or --confirm. "
                "Migrations are destructive and require explicit confirmation."
            )

        if dry_run and confirm:
            raise CommandError("Cannot specify both --dry-run and --confirm")

        # Get the model
        try:
            app_label, model_name = model_path.split(".")
            Model = apps.get_model(app_label, model_name)
        except (ValueError, LookupError) as e:
            raise CommandError(f'Invalid model path "{model_path}": {e}')

        # Check if model has required mixin fields
        required_fields = ["payment_provider", "payment_customer_id"]
        for field in required_fields:
            if not hasattr(Model, field):
                raise CommandError(
                    f'Model {model_path} must have field "{field}". '
                    f"Add PaymentProviderCustomerMixin to your model."
                )

        self.stdout.write(
            self.style.WARNING(
                f"\n{'=' * 70}\n"
                f"Payment Provider Migration\n"
                f"{'=' * 70}\n"
                f"From: {from_provider}\n"
                f"To:   {to_provider}\n"
                f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will make changes)'}\n"
                f"{'=' * 70}\n"
            )
        )

        # Find customers using the old provider
        customers = (
            Model.objects.filter(payment_provider=from_provider)
            .exclude(payment_customer_id__isnull=True)
            .exclude(payment_customer_id="")
        )

        count = customers.count()

        if count == 0:
            self.stdout.write(
                self.style.WARNING(f'No customers found using provider "{from_provider}"')
            )
            return

        self.stdout.write(f"\nFound {count} customers to migrate\n")

        # Import payment provider
        from swap_layer.billing import get_provider

        if not dry_run:
            # Temporarily switch to new provider
            original_provider = getattr(settings, "PAYMENT_PROVIDER", "stripe")
            settings.PAYMENT_PROVIDER = to_provider
            provider = get_provider()
            settings.PAYMENT_PROVIDER = original_provider

        migrated = 0
        failed = 0

        for customer in customers:
            customer_identifier = getattr(customer, "email", None) or str(customer.pk)

            if dry_run:
                self.stdout.write(
                    f"  [DRY RUN] Would migrate: {customer_identifier} "
                    f"({customer.payment_customer_id})"
                )
                migrated += 1
            else:
                try:
                    # Create customer in new provider
                    new_customer = provider.create_customer(
                        email=getattr(customer, "email", f"user{customer.pk}@example.com"),
                        name=getattr(customer, "name", None) or getattr(customer, "username", None),
                        metadata={
                            "migrated_from": from_provider,
                            "old_customer_id": customer.payment_customer_id,
                        },
                    )

                    # Update model
                    customer.payment_provider = to_provider
                    customer.payment_customer_id = new_customer["id"]
                    customer.save(update_fields=["payment_provider", "payment_customer_id"])

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✓ Migrated: {customer_identifier} → {new_customer['id']}"
                        )
                    )
                    migrated += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ Failed: {customer_identifier} - {str(e)}")
                    )
                    failed += 1

        # Summary
        self.stdout.write(f"\n{'=' * 70}")
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN COMPLETE\n"
                    f"Would migrate: {migrated} customers\n"
                    f"Run with --confirm to perform actual migration"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"MIGRATION COMPLETE\nMigrated: {migrated}\nFailed:   {failed}")
            )
            if failed > 0:
                self.stdout.write(
                    self.style.WARNING("\nSome migrations failed. Review errors above.")
                )

        self.stdout.write(f"{'=' * 70}\n")
