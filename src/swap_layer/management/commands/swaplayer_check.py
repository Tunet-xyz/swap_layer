"""
Django management command to check SwapLayer configuration.

Usage:
    python manage.py swaplayer_check
    python manage.py swaplayer_check --module payments
    python manage.py swaplayer_check --verbose
"""

from django.core.management.base import BaseCommand, CommandError

from swap_layer.settings import validate_swaplayer_config


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
        """Print configuration with sensitive values masked."""
        prefix = " " * indent

        for field_name, field_value in config.__dict__.items():
            if field_value is None:
                continue

            # Mask sensitive values
            if any(
                keyword in field_name.lower() for keyword in ["key", "secret", "token", "password"]
            ):
                if isinstance(field_value, str):
                    masked = (
                        field_value[:8] + "..." + field_value[-4:]
                        if len(field_value) > 12
                        else "***"
                    )
                    self.stdout.write(f"{prefix}{field_name}: {masked}")
                else:
                    self.stdout.write(f"{prefix}{field_name}: [MASKED]")
            elif isinstance(field_value, dict):
                self.stdout.write(f"{prefix}{field_name}:")
                for key, val in field_value.items():
                    if any(
                        keyword in key.lower() for keyword in ["key", "secret", "token", "password"]
                    ):
                        masked = "***"
                        self.stdout.write(f"{prefix}  {key}: {masked}")
                    else:
                        self.stdout.write(f"{prefix}  {key}: {val}")
            elif hasattr(field_value, "__dict__"):
                self.stdout.write(f"{prefix}{field_name}:")
                self._print_config(field_value, indent + 2)
            else:
                self.stdout.write(f"{prefix}{field_name}: {field_value}")
