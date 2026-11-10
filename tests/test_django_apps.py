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


def run_django(body: str) -> str:
    script = textwrap.dedent(
        f"""
        import json
        import django
        from django.conf import settings
        settings.configure(
            INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth", *{APPS!r}],
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
