"""Deprecated alias of ``swaplayer_migrate_billing_provider``, kept through 1.x."""

import warnings

from .swaplayer_migrate_billing_provider import Command as BillingProviderCommand

DEPRECATION = "migrate_payment_provider is deprecated: use swaplayer_migrate_billing_provider."


class Command(BillingProviderCommand):
    help = f"Deprecated alias of swaplayer_migrate_billing_provider. {BillingProviderCommand.help}"

    def handle(self, *args, **options):
        warnings.warn(DEPRECATION, DeprecationWarning, stacklevel=2)
        self.stderr.write(self.style.WARNING(DEPRECATION))
        return super().handle(*args, **options)
