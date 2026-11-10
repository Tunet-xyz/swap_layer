"""
Copy the README, SECURITY.md and docs guides into the packaged MCP guidance.

The installed ``swaplayer-mcp`` serves these copies through ``explain(topic)``
and the ``opensource://swap_layer/docs/<topic>`` resources, because a wheel has
no docs/ folder. Relative links become absolute GitHub links so they still work.

Run after editing any of the source Markdown files:

    python tools/sync_mcp_guidance.py

``tests/test_mcp_guidance.py`` fails while the packaged copies are out of date.
"""

from __future__ import annotations

import json
import posixpath
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDANCE = ROOT / "src" / "swap_layer" / "mcp" / "guidance.json"
REPOSITORY_BLOB = "https://github.com/Tunet-xyz/swap_layer/blob/main/"

# explain() topic -> repository Markdown file it copies.
TOPIC_SOURCES = {
    "overview": "README.md",
    "docs-index": "docs/README.md",
    "architecture": "docs/architecture.md",
    "billing": "docs/billing.md",
    "email": "docs/email.md",
    "sms": "docs/sms.md",
    "storage": "docs/storage.md",
    "identity-platform": "docs/identity-platform.md",
    "identity-verification": "docs/identity-verification.md",
    "mcp": "docs/mcp.md",
    "security": "SECURITY.md",
}
# Short topics written for the MCP guidance itself (no Markdown source).
HAND_WRITTEN_TOPICS = ("philosophy", "faq")

_INLINE_LINK = re.compile(r"(\]\()([^)\s]+)(\))")
_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def absolute_links(text: str, source: str) -> str:
    """Rewrite relative Markdown links in ``source`` to absolute GitHub links."""
    base = posixpath.dirname(source)

    def rewrite(match: re.Match[str]) -> str:
        target = match.group(2)
        if _SCHEME.match(target) or target.startswith(("#", "/")):
            return match.group(0)
        path, hash_mark, fragment = target.partition("#")
        resolved = posixpath.normpath(posixpath.join(base, path))
        return f"{match.group(1)}{REPOSITORY_BLOB}{resolved}{hash_mark}{fragment}{match.group(3)}"

    return _INLINE_LINK.sub(rewrite, text)


def packaged_topics(root: Path = ROOT) -> dict[str, str]:
    """Return every Markdown-sourced topic as the guidance should contain it."""
    topics = {}
    for topic, source in TOPIC_SOURCES.items():
        text = (root / source).read_text(encoding="utf-8").replace("\r\n", "\n")
        topics[topic] = absolute_links(text, source)
    return topics


def synced_guidance(guidance: dict, root: Path = ROOT) -> dict:
    """Return ``guidance`` with its explain topics refreshed from the Markdown files."""
    explain = packaged_topics(root)
    for topic in HAND_WRITTEN_TOPICS:
        explain[topic] = guidance["explain"][topic]
    return {**guidance, "explain": explain}


def render(guidance: dict) -> str:
    return json.dumps(guidance, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    current = json.loads(GUIDANCE.read_text(encoding="utf-8"))
    updated = synced_guidance(current)
    if "--check" in argv:
        if updated != current:
            print("guidance.json is out of date; run python tools/sync_mcp_guidance.py")
            return 1
        return 0
    GUIDANCE.write_text(render(updated), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
