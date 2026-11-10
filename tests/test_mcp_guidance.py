"""The packaged MCP guidance matches the repository docs and uses current names and installs."""

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
GUIDANCE = json.loads((ROOT / "src/swap_layer/mcp/guidance.json").read_text(encoding="utf-8"))

_spec = importlib.util.spec_from_file_location("sync_mcp_guidance", ROOT / "tools/sync_mcp_guidance.py")
assert _spec and _spec.loader
sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync)


def test_packaged_docs_match_the_repository():
    assert sync.synced_guidance(GUIDANCE) == GUIDANCE, (
        "README.md, SECURITY.md or docs/ changed: run python tools/sync_mcp_guidance.py"
    )


def test_overview_is_the_readme_with_the_family_line():
    overview = GUIDANCE["explain"]["overview"]
    assert overview.startswith("# SwapLayer\n")
    assert (
        "Part of the [Tunet](https://www.tunet.xyz/engineering/) open-source libraries, alongside "
        "[AccessGate](https://github.com/Tunet-xyz/access_gate), "
        "[GeoCanon](https://github.com/Tunet-xyz/geo_canon), and "
        "[SessionArmor](https://github.com/Tunet-xyz/session_armor)."
    ) in overview
    assert "Other Tunet libraries" not in overview


def test_packaged_links_are_absolute():
    for topic, text in GUIDANCE["explain"].items():
        for target in re.findall(r"\]\(([^)\s]+)\)", text):
            assert target.startswith(("https://", "http://", "mailto:", "#")), (topic, target)


def test_relative_links_resolve_against_their_source():
    text = sync.absolute_links("[a](billing.md) [b](../SECURITY.md#reporting) [c](https://x.example) [d](#top)", "docs/README.md")
    assert text == (
        "[a](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/billing.md) "
        "[b](https://github.com/Tunet-xyz/swap_layer/blob/main/SECURITY.md#reporting) "
        "[c](https://x.example) [d](#top)"
    )


def test_install_commands_follow_the_shared_form():
    installs = [
        entry["pip_install"]
        for section in ("quickstarts", "info")
        for providers in GUIDANCE[section].values()
        for entry in providers.values()
        if "pip_install" in entry
    ]
    assert installs
    for command in installs:
        assert re.fullmatch(r'pip install (SwapLayer|"SwapLayer\[[a-z0-9,]+\]")', command), command
    data = json.dumps({key: value for key, value in GUIDANCE.items() if key != "explain"})
    assert "==" not in data
    assert "pip install '" not in data
    assert "swaplayer_" not in data


def test_guidance_topics_are_served():
    from swap_layer.mcp.server import load_contract

    contract = load_contract()
    topics = contract["tools"][[t["name"] for t in contract["tools"]].index("explain")]
    assert set(topics["inputSchema"]["properties"]["topic"]["enum"]) == set(GUIDANCE["explain"])
    guides = {r["guide"] for r in contract["resources"] if "guide" in r}
    assert guides == set(sync.TOPIC_SOURCES)
