"""Release identities, public stdio recovery and executable settings examples."""

import ast
import json
import subprocess
import sys
from importlib import metadata
from pathlib import Path

import swap_layer
from swap_layer.mcp import create_mcp_server
from swap_layer.mcp.server import _GUIDANCE


def test_package_runtime_and_contract_versions_match():
    root = Path(__file__).parents[1]
    packaged = root / "src/swap_layer/mcp/agent-contract.json"
    public = root / "mcp/agent-contract.json"
    assert packaged.read_bytes() == public.read_bytes()
    assert metadata.version("SwapLayer") == swap_layer.__version__ == "1.0.0"
    assert json.loads(public.read_text(encoding="utf-8"))["server"]["version"] == swap_layer.__version__
    assert create_mcp_server().create_initialization_options().server_version == swap_layer.__version__


def test_guidance_settings_examples_validate(monkeypatch):
    fixtures = {
        "STRIPE_SECRET_KEY": "sk_test_fixture", "TWILIO_ACCOUNT_SID": "ACfixture",
        "TWILIO_FROM_NUMBER": "+15555551234", "WORKOS_COOKIE_PASSWORD": "fixture-cookie-password" * 3,
    }
    count = 0
    for service in _GUIDANCE["quickstarts"].values():
        for quickstart in service.values():
            source = quickstart["settings_config"]
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Subscript) and ast.unparse(node.value) == "os.environ" and isinstance(node.slice, ast.Constant):
                    key = node.slice.value
                    monkeypatch.setenv(key, fixtures.get(key, "fixture-value"))
            namespace = {}
            exec(compile(tree, "<release-settings-example>", "exec"), namespace)
            assert namespace["SWAPLAYER"] is not None
            ast.parse(quickstart["usage_example"])
            count += 1
    assert count >= 15


def test_public_stdio_recovers_and_reports_release_version():
    script = Path(__file__).parents[1] / "mcp/server.py"
    messages = '\n'.join([
        '{"jsonrpc":"2.0","id":1,"method":"ping","method":"ping"}',
        json.dumps({"jsonrpc":"2.0", "id":2, "method":"initialize", "params":{}}),
        json.dumps({"jsonrpc":"2.0", "id":3, "method":"ping"}),
    ]) + '\n'
    result = subprocess.run([sys.executable, str(script)], input=messages, capture_output=True, text=True, encoding="utf-8", timeout=15, check=True)
    responses = [json.loads(line) for line in result.stdout.splitlines()]
    assert "error" in responses[0]
    assert responses[1]["result"]["serverInfo"]["version"] == "1.0.0"
    assert responses[2]["id"] == 3 and responses[2]["result"] == {}
