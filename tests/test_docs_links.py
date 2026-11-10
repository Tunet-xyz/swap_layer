"""Repository links in packaged code and data point at files that exist."""

import re
from pathlib import Path

import pytest

from swap_layer.exceptions import (
    MODULE_DOCS,
    ModuleNotConfiguredError,
    ProviderConfigMismatchError,
    module_docs_url,
)

ROOT = Path(__file__).parents[1]
BLOB = re.compile(r"https://github\.com/Tunet-xyz/swap_layer/(?:blob|tree)/main/([\w./-]+)")


@pytest.mark.parametrize(
    ("module", "guide"),
    [
        ("billing", "billing.md"),
        ("communications.sms", "sms.md"),
        ("sms", "sms.md"),
        ("communications.email", "email.md"),
        ("storage", "storage.md"),
        ("identity", "identity-platform.md"),
        ("verification", "identity-verification.md"),
        ("communications", "README.md"),
    ],
)
def test_module_errors_link_to_their_guide(module, guide):
    assert module_docs_url(module).endswith(f"/blob/main/docs/{guide}")
    assert ModuleNotConfiguredError(module).docs_url == module_docs_url(module)
    assert ProviderConfigMismatchError(module, "x", "x").docs_url == module_docs_url(module)


def test_every_module_guide_exists():
    for guide in MODULE_DOCS.values():
        assert (ROOT / "docs" / guide).is_file(), guide


def test_repository_links_in_the_package_exist():
    files = [p for p in (ROOT / "src" / "swap_layer").rglob("*") if p.suffix in {".py", ".json"}]
    links = {match for path in files for match in BLOB.findall(path.read_text(encoding="utf-8"))}
    assert links, "expected repository links in the package"
    missing = sorted(link for link in links if not (ROOT / link.rstrip("/.")).exists())
    assert missing == []
