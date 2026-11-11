"""Every SwapLayer Django app loads, and docstring import examples resolve."""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytest.importorskip("django")

SRC = Path(__file__).parents[1] / "src"
APPS = [
    "swap_layer",
    "swap_layer.billing",
    "swap_layer.communications.email",
    "swap_layer.communications.sms",
    "swap_layer.identity.platform",
    "swap_layer.identity.verification",
    "swap_layer.storage",
]


def run_django(body: str, apps: list[str] = APPS) -> str:
    script = textwrap.dedent(
        f"""
        import json
        import warnings
        warnings.simplefilter("always", DeprecationWarning)
        import django
        from django.conf import settings
        settings.configure(
            INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth", *{apps!r}],
            DATABASES={{"default": {{"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}}},
            SECRET_KEY="test",
        )
        django.setup()
        """
    ) + textwrap.dedent(body)
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    env.pop("DJANGO_SETTINGS_MODULE", None)
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, env=env, timeout=120
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_every_app_loads_with_its_module_path():
    output = run_django(
        """
        from django.apps import apps
        print(json.dumps({c.name: c.label for c in apps.get_app_configs()}))
        """
    )
    labels = json.loads(output)
    assert set(APPS) <= set(labels)


EXPECTED = {
    "swap_layer.billing": ["swap_layer_billing", "BillingAppConfig"],
    "swap_layer.communications.email": ["swap_layer_email", "EmailAppConfig"],
    "swap_layer.communications.sms": ["swap_layer_sms", "SMSAppConfig"],
    "swap_layer.identity.platform": ["swap_layer_identity_platform", "IdentityPlatformAppConfig"],
    "swap_layer.identity.verification": [
        "swap_layer_identity_verification",
        "IdentityVerificationAppConfig",
    ],
    "swap_layer.storage": ["swap_layer_storage", "StorageAppConfig"],
}


def test_apps_use_prefixed_labels_and_area_class_names():
    output = run_django(
        """
        from django.apps import apps
        print(json.dumps({c.name: [c.label, type(c).__name__] for c in apps.get_app_configs()}))
        """
    )
    configs = json.loads(output)
    assert {name: configs[name] for name in EXPECTED} == EXPECTED


def test_management_commands_share_the_swaplayer_prefix():
    output = run_django(
        """
        from django.core.management import get_commands
        commands = get_commands()
        names = ["swaplayer_check", "swaplayer_migrate_billing_provider", "migrate_payment_provider"]
        print(json.dumps({name: commands.get(name) for name in names}))
        """
    )
    assert json.loads(output) == {
        "swaplayer_check": "swap_layer",
        "swaplayer_migrate_billing_provider": "swap_layer.billing",
        "migrate_payment_provider": "swap_layer.billing",  # deprecated alias, kept through 1.x
    }


def test_former_class_paths_still_load_with_a_deprecation_warning():
    former = [
        "swap_layer.billing.apps.BillingConfig",
        "swap_layer.communications.email.apps.EmailConfig",
        "swap_layer.communications.sms.apps.SmsConfig",
        "swap_layer.identity.platform.apps.AuthenticationConfig",
        "swap_layer.identity.verification.apps.IdentityConfig",
        "swap_layer.storage.apps.StorageConfig",
    ]
    output = run_django(
        """
        from django.apps import apps
        print(json.dumps(sorted(type(c).__name__ for c in apps.get_app_configs())))
        """,
        apps=former,
    )
    loaded = json.loads(output.splitlines()[-1])
    assert {name for _, name in EXPECTED.values()} <= set(loaded)


def docstring_imports() -> list[tuple[str, str]]:
    import ast
    import re

    pattern = re.compile(r"^\s*(?:>>>\s*)?from\s+(swap_layer[\w.]*)\s+import\s+([\w, ]+)\s*$")
    found = []
    for path in sorted((SRC / "swap_layer").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                for line in (ast.get_docstring(node, clean=False) or "").splitlines():
                    match = pattern.match(line)
                    if match:
                        found += [(match.group(1), name.strip()) for name in match.group(2).split(",")]
    return found


def test_docstring_import_examples_resolve():
    imports = docstring_imports()
    assert len(imports) >= 30
    output = run_django(
        f"""
        import importlib
        missing = []
        for module, name in {imports!r}:
            try:
                if not hasattr(importlib.import_module(module), name):
                    missing.append(f"{{module}}.{{name}}")
            except ImportError:
                missing.append(f"{{module}}.{{name}}")
        print(json.dumps(missing))
        """
    )
    assert json.loads(output) == []


@pytest.mark.parametrize(
    ("module", "former", "current"),
    [
        ("swap_layer.billing.apps", "BillingConfig", "BillingAppConfig"),
        ("swap_layer.communications.email.apps", "EmailConfig", "EmailAppConfig"),
        ("swap_layer.communications.sms.apps", "SmsConfig", "SMSAppConfig"),
        ("swap_layer.identity.platform.apps", "AuthenticationConfig", "IdentityPlatformAppConfig"),
        ("swap_layer.identity.verification.apps", "IdentityConfig", "IdentityVerificationAppConfig"),
        ("swap_layer.storage.apps", "StorageConfig", "StorageAppConfig"),
    ],
)
def test_former_class_names_warn(module, former, current):
    import importlib

    apps_module = importlib.import_module(module)
    with pytest.warns(DeprecationWarning, match=current):
        assert getattr(apps_module, former) is getattr(apps_module, current)
    with pytest.raises(AttributeError):
        apps_module.NoSuchConfig  # noqa: B018
