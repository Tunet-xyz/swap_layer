"""SwapLayer's MCP server: one stdio server that serves its public contract."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from swap_layer.mcp import server
from swap_layer.mcp.server import (
    SERVICES,
    TOOL_HANDLERS,
    _compare_providers,
    _explain,
    _get_migration_guide,
    _get_provider_info,
    _list_providers,
    _troubleshoot,
    get_prompt,
    load_contract,
)

ROOT = Path(__file__).parents[1]
CONTRACT = load_contract()
TOOLS = {tool["name"]: tool for tool in CONTRACT["tools"]}
CAMEL_CASE = re.compile(r"^[a-z][a-z0-9]*(?:[A-Z][a-z0-9]*)*$")
SNAKE_CASE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


def run_stdio(*messages: dict, script: Path | None = None) -> list[dict]:
    """Send JSON-RPC messages to a fresh server process and return its responses."""
    command = [sys.executable, str(script)] if script else [sys.executable, "-m", "swap_layer.mcp"]
    payload = "\n".join(json.dumps(message) for message in messages) + "\n"
    env = {"PYTHONPATH": str(ROOT / "src"), "AWS_EC2_METADATA_DISABLED": "true"}
    import os

    completed = subprocess.run(
        command, input=payload, capture_output=True, text=True, encoding="utf-8",
        timeout=180, check=True, env={**os.environ, **env},  # a cold start on a busy machine can be slow
    )
    return [json.loads(line) for line in completed.stdout.splitlines()]


def request(request_id: int, method: str, **params) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}


# ---------------------------------------------------------------------------
# Contract and naming
# ---------------------------------------------------------------------------


def test_every_contract_tool_runs_and_every_handler_is_in_the_contract():
    assert set(TOOLS) == set(TOOL_HANDLERS)
    runtime = {name for name, tool in TOOLS.items() if tool["executionMode"] == "runtime"}
    apis = next(r for r in CONTRACT["resources"] if r["name"] == "public-apis")["data"]
    assert set(apis["mcpRuntimeTools"]) == runtime


def test_names_follow_the_shared_convention():
    for name, tool in TOOLS.items():
        assert SNAKE_CASE.match(name) and not name.startswith("swaplayer"), name
        for argument in tool["inputSchema"]["properties"]:
            assert CAMEL_CASE.match(argument), f"{name}.{argument}"
    for prompt in CONTRACT["prompts"]:
        for argument in prompt["arguments"]:
            assert SNAKE_CASE.match(argument["name"]), f"{prompt['name']}.{argument['name']}"
    assert all(r["uri"].startswith("opensource://swap_layer/") for r in CONTRACT["resources"])


def test_service_arguments_use_billing():
    for tool in TOOLS.values():
        service = tool["inputSchema"]["properties"].get("service")
        if service:
            assert set(SERVICES) <= set(service["enum"]), tool["name"]
            assert "payments" not in service["enum"], tool["name"]
    guidance_keys = json.dumps({k: list(v) for k, v in server._GUIDANCE.items() if k != "explain"})
    assert "payments" not in guidance_keys


def test_contract_uses_the_shared_key_set():
    access = CONTRACT["publicAccess"]
    assert "runtimeServer" not in CONTRACT["server"]
    assert access["mcpEndpoint"] == (
        "swaplayer-mcp stdio server installed with the package; "
        "python mcp/server.py from a source checkout"
    )
    assert access["djangoAdapter"].startswith('pip install "SwapLayer[django]"')
    assert "cli" in access["supportedOperationModes"]
    assert access["browserAutomation"]["allowed"] is True
    assert access["cli"] == ["swaplayer-mcp"]


def test_side_effect_tools_are_marked():
    for name in ("send_test_email", "send_test_sms", "check_storage"):
        annotations = TOOLS[name]["annotations"]
        assert annotations["readOnlyHint"] is False and annotations["openWorldHint"] is True
    for name, tool in TOOLS.items():
        if name not in {"send_test_email", "send_test_sms", "check_storage"}:
            assert tool["annotations"]["readOnlyHint"] is True, name


def test_console_script_and_checkout_shim_run_the_packaged_server():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'swaplayer-mcp = "swap_layer.mcp.server:main"' in pyproject
    shim = (ROOT / "mcp" / "server.py").read_text(encoding="utf-8")
    assert "from swap_layer.mcp.server import main" in shim


# ---------------------------------------------------------------------------
# stdio protocol
# ---------------------------------------------------------------------------


def test_stdio_server_reports_the_contract_identity_and_surfaces():
    responses = run_stdio(
        request(1, "initialize"),
        request(2, "tools/list"),
        request(3, "resources/list"),
        request(4, "prompts/list"),
    )
    info = responses[0]["result"]["serverInfo"]
    assert info["name"] == CONTRACT["server"]["name"] == "swap-layer-public-contract-mcp"
    assert info["version"] == CONTRACT["server"]["version"]
    assert [t["name"] for t in responses[1]["result"]["tools"]] == list(TOOLS)
    uris = [r["uri"] for r in responses[2]["result"]["resources"]]
    assert uris[0] == "opensource://swap_layer/agent-contract"
    assert all(uri.startswith("opensource://swap_layer/") for uri in uris)
    assert {p["name"] for p in responses[3]["result"]["prompts"]} == {
        "agent_onboarding", "onboard_service", "choose_provider", "migrate_provider"
    }


def test_every_resource_can_be_read():
    uris = ["opensource://swap_layer/agent-contract", *[r["uri"] for r in CONTRACT["resources"]]]
    responses = run_stdio(*[request(i, "resources/read", uri=uri) for i, uri in enumerate(uris)])
    for uri, response in zip(uris, responses, strict=True):
        (content,) = response["result"]["contents"]
        assert content["uri"] == uri and len(content["text"]) > 50, uri
    readme = next(r for r in responses if r["result"]["contents"][0]["uri"].endswith("/docs/overview"))
    assert "alongside [AccessGate](https://github.com/Tunet-xyz/access_gate)" in readme["result"]["contents"][0]["text"]


def test_runtime_tools_run_over_stdio():
    responses = run_stdio(
        request(1, "tools/call", name="list_providers", arguments={"service": "billing"}),
        request(2, "tools/call", name="explain", arguments={"topic": "storage"}),
        request(3, "tools/call", name="prepare_provider_setup",
                arguments={"service": "billing", "provider": "stripe", "projectType": "new"}),
        request(4, "tools/call", name="plan_provider_migration",
                arguments={"service": "billing", "fromProvider": "stripe", "toProvider": "paypal"}),
        request(5, "tools/call", name="describe_offering", arguments={}),
        request(6, "tools/call", name="list_public_capabilities", arguments={"surface": "mcp-tools"}),
        request(7, "tools/call", name="map_workflow_to_tools", arguments={"workflow": "migrate provider"}),
        request(8, "tools/call", name="operate_browser_docs", arguments={"task": "read docs"}),
    )
    results = [response["result"] for response in responses]
    assert all(r["isError"] is False for r in results)
    assert results[0]["structuredContent"]["providers"] == ["stripe", "paypal", "square"]
    assert "# Storage" in results[1]["structuredContent"]["content"]
    assert results[2]["structuredContent"]["pip_install"] == 'pip install "SwapLayer[stripe]"'
    assert "provider_info" in results[2]["structuredContent"]
    assert "customer" in results[3]["structuredContent"]["data_migration_note"].lower()
    assert results[4]["structuredContent"]["offering"]["id"] == "swap_layer"
    assert results[5]["structuredContent"]["capabilities"]["mcp-tools"] == list(TOOLS)
    assert results[6]["structuredContent"]["matched"] is True
    assert results[7]["structuredContent"]["publicPages"]["pypi"] == "https://pypi.org/project/SwapLayer/"
    assert json.loads(results[0]["content"][0]["text"]) == results[0]["structuredContent"]


@pytest.mark.parametrize(
    ("name", "arguments", "expected"),
    [
        ("swaplayer_get_config", {"service": "all"}, "swaplayer_get_config"),  # former names are gone
        ("check_storage", {"test_upload": True}, "accepted: testUpload"),
        ("list_providers", {"service": "payments"}, "must be one of"),
        ("list_providers", {}, "Missing required arguments"),
        ("check_storage", {"testUpload": "yes"}, "must be a boolean"),
    ],
)
def test_invalid_tool_calls_are_rejected(name, arguments, expected):
    (response,) = run_stdio(request(1, "tools/call", name=name, arguments=arguments))
    assert response["error"]["code"] == -32602
    assert expected in response["error"]["message"]


def test_checkout_shim_serves_the_same_server():
    (response,) = run_stdio(request(1, "initialize"), script=ROOT / "mcp" / "server.py")
    assert response["result"]["serverInfo"]["name"] == "swap-layer-public-contract-mcp"


def test_prompt_arguments_cannot_inject_other_placeholders():
    prompt = get_prompt(
        CONTRACT, "migrate_provider",
        {"service": "{to_provider}" * 3, "from_provider": "stripe", "to_provider": "x" * 10},
    )
    text = prompt["messages"][0]["content"]["text"]
    assert "{to_provider}{to_provider}{to_provider}" in text
    assert text.count("x" * 10) == 2  # only the two real {to_provider} placeholders
    optional = get_prompt(CONTRACT, "choose_provider", {"service": "sms"})
    assert "My requirements: not stated." in optional["messages"][0]["content"]["text"]
    with pytest.raises(ValueError, match="Missing required prompt argument"):
        get_prompt(CONTRACT, "onboard_service", {"service": "sms"})
    with pytest.raises(ValueError, match="Unknown prompt arguments"):
        get_prompt(CONTRACT, "onboard_service", {"service": "sms", "provider": "twilio", "extra": "x"})


# ---------------------------------------------------------------------------
# MCP SDK adapter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sdk_server_serves_the_same_contract():
    types = pytest.importorskip("mcp.types")
    sdk_server = server.create_mcp_server()
    assert sdk_server.name == CONTRACT["server"]["name"]

    tools = await sdk_server.request_handlers[types.ListToolsRequest](
        types.ListToolsRequest(method="tools/list")
    )
    assert [t.name for t in tools.root.tools] == list(TOOLS)

    call = await sdk_server.request_handlers[types.CallToolRequest](
        types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(name="list_providers", arguments={"service": "sms"}),
        )
    )
    assert call.root.isError is False
    assert call.root.structuredContent["providers"] == ["twilio", "sns"]

    read = await sdk_server.request_handlers[types.ReadResourceRequest](
        types.ReadResourceRequest(
            method="resources/read",
            params=types.ReadResourceRequestParams(uri="opensource://swap_layer/docs/billing"),
        )
    )
    assert "# Billing" in read.root.contents[0].text

    prompt = await sdk_server.request_handlers[types.GetPromptRequest](
        types.GetPromptRequest(
            method="prompts/get",
            params=types.GetPromptRequestParams(name="agent_onboarding", arguments={"user_goal": "send SMS"}),
        )
    )
    assert "send SMS" in prompt.root.messages[0].content.text


def test_sdk_server_needs_the_mcp_extra(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def without_mcp(name, *args, **kwargs):
        if name == "mcp" or name.startswith("mcp."):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", without_mcp)
    with pytest.raises(ImportError, match=r'SwapLayer\[mcp\]'):
        server.create_mcp_server()


# ---------------------------------------------------------------------------
# Runtime tool implementations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_providers():
    result = await _list_providers("email")
    assert result["status"] == "success"
    assert set(result["providers"]) == {"django", "smtp"}
    assert "stripe" in (await _list_providers("billing"))["providers"]
    assert (await _list_providers("payments"))["status"] == "error"


@pytest.mark.asyncio
async def test_get_provider_info():
    result = await _get_provider_info("billing", "stripe")
    assert result["status"] == "success"
    assert {"description", "capabilities"} <= set(result["info"])
    assert (await _get_provider_info("email", "sendgrid"))["provider"] == "sendgrid"
    assert (await _get_provider_info("email", "invalid"))["status"] == "error"


@pytest.mark.asyncio
async def test_explain_every_topic():
    topics = TOOLS["explain"]["inputSchema"]["properties"]["topic"]["enum"]
    for topic in topics:
        result = await _explain(topic)
        assert result["status"] == "success", topic
        assert len(result["content"]) > 100, topic
        assert result["format"] == "markdown"
        assert set(result["related_tools"]) <= set(TOOLS), topic
    assert (await _explain("nonexistent"))["status"] == "error"


@pytest.mark.asyncio
async def test_compare_providers():
    for service in SERVICES:
        result = await _compare_providers(service)
        assert result["status"] == "success", service
        assert len(result["providers"]) >= (1 if service == "verification" else 2)
    result = await _compare_providers("email", use_case="aws high volume private-text")
    assert "private-text" not in json.dumps(result)
    assert (await _compare_providers("nonexistent"))["status"] == "error"


@pytest.mark.asyncio
async def test_troubleshoot():
    for scenario in TOOLS["troubleshoot"]["inputSchema"]["properties"]["scenario"]["enum"]:
        result = await _troubleshoot(scenario)
        assert result["status"] == "success", scenario
        assert result["symptoms"] and result["cause"] and result["solution"]
    error_message = "ImportError: No module named 'stripe' token=sk_live_private"
    result = await _troubleshoot("missing_package", error_message=error_message)
    assert "symptom_matched" in result
    # The pasted text is matched, never echoed back (it may contain credentials).
    assert "sk_live_private" not in json.dumps(result)
    assert (await _troubleshoot("nonexistent_problem"))["status"] == "error"


@pytest.mark.asyncio
async def test_migration_guide():
    result = await _get_migration_guide("email", "sendgrid", "mailgun")
    assert result["status"] == "success"
    assert result["application_code_changes"] == "review-required"
    assert "sendgrid" in result["guide"].lower() and "mailgun" in result["guide"].lower()
    billing = await _get_migration_guide("billing", "stripe", "paypal")
    assert "customer" in billing["data_migration_note"].lower()
    assert (await _get_migration_guide("unknown_service", "a", "b"))["status"] == "error"
    assert (await _get_migration_guide("email", "sendgrid", "unknown"))["warnings"]


@pytest.mark.parametrize(
    ("path", "servers_key"),
    [("docs/mcp-config-example.json", "mcpServers"), ("examples/vscode-mcp.json", "servers")],
)
def test_client_config_examples_start_the_server_with_real_settings(path, servers_key):
    from swap_layer.settings import SwapLayerSettings, _env_path

    config = json.loads((ROOT / path).read_text(encoding="utf-8"))
    (name, entry), = config[servers_key].items()
    assert name == entry["command"] == "swaplayer-mcp"
    assert "DJANGO_SETTINGS_MODULE" not in entry["env"]  # the CLI reads SWAPLAYER_ variables
    for variable in entry["env"]:
        assert variable.startswith("SWAPLAYER_"), variable
        parts = variable.removeprefix("SWAPLAYER_").lower().split("_")
        assert _env_path(SwapLayerSettings, parts) is not None, variable
