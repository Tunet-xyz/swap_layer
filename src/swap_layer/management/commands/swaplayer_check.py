"""
Django management command to check SwapLayer configuration.

Usage:
    python manage.py swaplayer_check
    python manage.py swaplayer_check --module payments
    python manage.py swaplayer_check --verbose
"""

from django.core.management.base import BaseCommand, CommandError

from swap_layer._redaction import redact_config
from swap_layer.settings import validate_swaplayer_config

# Credential values are replaced by this marker; no characters are shown.
SECRET_MASK = "********"


class Command(BaseCommand):
    help = "Check SwapLayer configuration and display status"

    def add_arguments(self, parser):
        parser.add_argument(
            "--module",
            type=str,
            help="Check specific module (billing, communications, storage, identity, verification)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed configuration (masks sensitive values)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO("=" * 60))
        self.stdout.write(self.style.HTTP_INFO("SwapLayer Configuration Check"))
        self.stdout.write(self.style.HTTP_INFO("=" * 60))
        self.stdout.write("")

        # Validate configuration
        result = validate_swaplayer_config()

        if not result["valid"]:
            self.stdout.write(self.style.ERROR("✗ Configuration Invalid"))
            self.stdout.write(self.style.ERROR(f"  Error: {result['error']}"))
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Hint: Make sure SWAPLAYER is configured in your Django settings.py"
                )
            )
            self.stdout.write("")
            self.stdout.write("Example configuration:")
            self.stdout.write("")
            self.stdout.write("    SWAPLAYER = {")
            self.stdout.write('        "billing": {')
            self.stdout.write('            "provider": "stripe",')
            self.stdout.write('            "stripe": {"secret_key": "sk_test_..."}')
            self.stdout.write("        },")
            self.stdout.write('        "email": {"provider": "django"},')
            self.stdout.write("    }")
            raise CommandError("SwapLayer configuration is invalid")

        settings = result["settings"]
        modules_status = result["modules"]

        # Filter by module if specified
        if options["module"]:
            module = options["module"]
            if module not in modules_status:
                raise CommandError(f"Unknown module: {module}")
            modules_status = {module: modules_status[module]}

        # Display status for each module
        configured_count = 0
        for module, status in modules_status.items():
            if status.startswith("configured"):
                self.stdout.write(self.style.SUCCESS(f"✓ {module:15s} {status}"))
                configured_count += 1
            elif status == "not configured":
                self.stdout.write(self.style.WARNING(f"○ {module:15s} {status}"))
            else:
                self.stdout.write(self.style.ERROR(f"✗ {module:15s} {status}"))

        self.stdout.write("")

        # Summary
        total_modules = len(modules_status)
        self.stdout.write(
            self.style.HTTP_INFO(f"Configured: {configured_count}/{total_modules} modules")
        )

        # Verbose output
        if options["verbose"] and configured_count > 0:
            self.stdout.write("")
            self.stdout.write(self.style.HTTP_INFO("Detailed Configuration:"))
            self.stdout.write(self.style.HTTP_INFO("-" * 60))

            for module in modules_status.keys():
                config = getattr(settings, module, None)
                if config:
                    self.stdout.write("")
                    self.stdout.write(self.style.HTTP_INFO(f"{module.upper()}:"))
                    self._print_config(config, indent=2)

        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("=" * 60))

        if configured_count == 0:
            self.stdout.write(self.style.WARNING("No modules configured yet."))
            self.stdout.write("")
            self.stdout.write("Get started by configuring your first module in settings.py")
        else:
            self.stdout.write(self.style.SUCCESS("Configuration looks good! 🚀"))

        self.stdout.write(self.style.HTTP_INFO("=" * 60))

    def _print_config(self, config, indent=0):
        """Print configuration; every non-public value is masked completely."""
        self._print_value(redact_config(config, mask=SECRET_MASK), indent)

    def _print_value(self, value, indent):
        prefix = " " * indent
        if isinstance(value, dict):
            for key, item in value.items():
                if item is None:
                    continue
                if isinstance(item, (dict, list)):
                    self.stdout.write(f"{prefix}{key}:")
                    self._print_value(item, indent + 2)
                else:
                    self.stdout.write(f"{prefix}{key}: {item}")
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, (dict, list)):
                    self.stdout.write(f"{prefix}-")
                    self._print_value(item, indent + 2)
                else:
                    self.stdout.write(f"{prefix}- {item}")
