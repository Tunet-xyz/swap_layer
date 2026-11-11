"""
SwapLayer MCP server.

``swaplayer-mcp`` is one local stdio server. It serves SwapLayer's public agent
contract (``agent-contract.json``): its resources, tools and prompts, under
the ``opensource://swap_layer/`` scheme and with the contract's server name.
Tools whose contract ``executionMode`` is ``runtime`` run against the caller's
own SwapLayer configuration and provider accounts.

The stdio server needs no MCP SDK. ``create_mcp_server()`` builds an MCP SDK
server from the same contract for programmatic use (``SwapLayer[mcp]``).
"""

from __future__ import annotations

import asyncio
import io
import json
import math
import pathlib
import re
import sys
import uuid
from collections.abc import Awaitable, Callable, Mapping
from io import BytesIO
from typing import Any, cast

from swap_layer._redaction import redact_config

PROTOCOL_VERSION = "2025-06-18"
CONTRACT_PATH = pathlib.Path(__file__).with_name("agent-contract.json")
MAX_MESSAGE_CHARS = 1_100_000
MAX_JSON_NUMBER_CHARS = 256
MAX_ERROR_DETAIL_CHARS = 200
# Service keys used by the runtime tools (settings and get_provider() use the same names).
SERVICES = ("billing", "email", "sms", "storage", "identity", "verification")

# Packaged guidance works from wheels without a source checkout or Django.
_GUIDANCE: dict[str, Any] = json.loads(
    pathlib.Path(__file__).with_name("guidance.json").read_text(encoding="utf-8")
)
_EXPLAIN_TOPICS: dict[str, str] = _GUIDANCE["explain"]
_PROVIDER_COMPARISONS: dict[str, Any] = _GUIDANCE["comparisons"]
_TROUBLESHOOT_SCENARIOS: dict[str, Any] = _GUIDANCE["troubleshoot"]

# Storage probe files are written, then deleted, under this prefix.
STORAGE_CHECK_PREFIX = "swaplayer-mcp-check/"


def _redact_config(value: Any) -> Any:
    """Return configuration with every non-public field omitted, recursively."""
    return redact_config(value)


def load_contract() -> dict[str, Any]:
    """Load the packaged public agent contract."""
    with CONTRACT_PATH.open("r", encoding="utf-8") as handle:
        return cast(dict[str, Any], json.load(handle))


# ---------------------------------------------------------------------------
# JSON-RPC message handling
# ---------------------------------------------------------------------------


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Unsupported JSON constant: {value}")


def _reject_duplicate_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON object key: {key}")
        value[key] = item
    return value


def _parse_json_integer(value: str) -> int:
    if len(value) > MAX_JSON_NUMBER_CHARS:
        raise ValueError("JSON integer exceeds the digit limit.")
    return int(value)


def _parse_json_float(value: str) -> float:
    if len(value) > MAX_JSON_NUMBER_CHARS:
        raise ValueError("JSON number exceeds the digit limit.")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("JSON numbers must be finite.")
    return number


def parse_message(document: str) -> object:
    if not isinstance(document, str):
        raise TypeError("MCP messages must be strings.")
    if len(document) > MAX_MESSAGE_CHARS:
        raise ValueError("MCP message exceeds the size limit.")
    try:
        document.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError("MCP messages must be valid UTF-8.") from error
    return json.loads(
        document,
        parse_constant=_reject_json_constant,
        parse_float=_parse_json_float,
        parse_int=_parse_json_integer,
        object_pairs_hook=_reject_duplicate_json_object,
    )


def compact_json(value: Any) -> str:
    # ASCII output is valid UTF-8 under any locale and keeps lone surrogates as escapes.
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def write_message(message: dict[str, Any]) -> None:
    try:
        document = compact_json(message)
    except (RecursionError, TypeError, ValueError):
        request_id = message.get("id")
        if isinstance(request_id, bool) or not isinstance(request_id, str | int):
            request_id = None
        document = compact_json(error(request_id, -32603, "Internal error"))
    sys.stdout.write(document + "\n")
    sys.stdout.flush()


def result(request_id: Any, payload: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def error(request_id: Any, code: int, message: str, data: Any | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        body["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": body}


def _shorten(value: object) -> str:
    """Cut text quoted back from the client to MAX_ERROR_DETAIL_CHARS characters."""
    text = str(value)
    if len(text) > MAX_ERROR_DETAIL_CHARS:
        return text[:MAX_ERROR_DETAIL_CHARS] + "..."
    return text


# ---------------------------------------------------------------------------
# Contract resources and prompts
# ---------------------------------------------------------------------------


def _contract_resource_uri(contract: dict[str, Any]) -> str:
    return f"opensource://{contract['offering']['id']}/agent-contract"


def list_resources(contract: dict[str, Any]) -> dict[str, Any]:
    resources = [
        {
            "uri": _contract_resource_uri(contract),
            "name": "agent-contract",
            "title": "Full Agent Contract",
            "description": "The complete public MCP operating contract for this open-source offering.",
            "mimeType": "application/json",
        }
    ]
    for resource in contract.get("resources", []):
        resources.append(
            {
                "uri": resource["uri"],
                "name": resource.get("name", resource["uri"].rsplit("/", 1)[-1]),
                "title": resource.get("title", resource.get("name", resource["uri"])),
                "description": resource.get("description", ""),
                "mimeType": resource.get("mimeType", "application/json"),
            }
        )
    return {"resources": resources}


def read_resource(contract: dict[str, Any], uri: str) -> dict[str, Any]:
    if uri == _contract_resource_uri(contract):
        return {
            "contents": [{"uri": uri, "mimeType": "application/json", "text": pretty_json(contract)}]
        }
    for resource in contract.get("resources", []):
        if resource.get("uri") != uri:
            continue
        if "guide" in resource:
            text: Any = _EXPLAIN_TOPICS[resource["guide"]]
        else:
            text = resource.get("content")
            if text is None:
                text = pretty_json(resource.get("data", resource))
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": resource.get("mimeType", "application/json"),
                    "text": text if isinstance(text, str) else pretty_json(text),
                }
            ]
        }
    raise KeyError(uri)


def list_prompts(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "prompts": [
            {
                "name": prompt["name"],
                "title": prompt.get("title", prompt["name"].replace("_", " ").title()),
                "description": prompt.get("description", ""),
                "arguments": prompt.get("arguments", []),
            }
            for prompt in contract.get("prompts", [])
        ]
    }


_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


def get_prompt(contract: dict[str, Any], name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    prompt = next((p for p in contract.get("prompts", []) if p.get("name") == name), None)
    if prompt is None:
        raise KeyError(name)
    declared = {argument["name"]: argument for argument in prompt.get("arguments", [])}
    unknown = sorted(set(arguments) - set(declared))
    if unknown:
        raise ValueError(f"Unknown prompt arguments: {', '.join(unknown)}")
    values: dict[str, str] = {}
    for key, argument in declared.items():
        value = arguments.get(key)
        if value is None or value == "":
            if argument.get("required"):
                raise ValueError(f"Missing required prompt argument: {key}")
            value = "not stated"
        if not isinstance(value, str):
            raise TypeError(f"Prompt argument {key} must be a string")
        values[key] = value
    # One pass: text inside an argument is never read as another placeholder.
    text = _PLACEHOLDER.sub(
        lambda match: values.get(match.group(1), match.group(0)), prompt.get("template", "")
    )
    return {
        "description": prompt.get("description", ""),
        "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
    }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


def list_tools(contract: dict[str, Any]) -> dict[str, Any]:
    tools = []
    for tool in contract.get("tools", []):
        tools.append(
            {
                "name": tool["name"],
                "title": tool.get("title", tool["name"].replace("_", " ").title()),
                "description": tool.get("description", ""),
                "inputSchema": tool.get("inputSchema", {"type": "object", "properties": {}}),
                **({"outputSchema": tool["outputSchema"]} if "outputSchema" in tool else {}),
                "annotations": tool.get("annotations", {}),
            }
        )
    return {"tools": tools}


_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "boolean": (bool,),
    "integer": (int,),
    "number": (int, float),
    "object": (dict,),
    "array": (list,),
}


def _validated_arguments(tool: dict[str, Any], arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Check arguments against the tool's input schema; values are never echoed."""
    schema = tool.get("inputSchema") or {}
    properties: dict[str, Any] = schema.get("properties", {})
    unknown = sorted(set(arguments) - set(properties))
    if unknown:
        allowed = ", ".join(sorted(properties)) or "none"
        raise ValueError(f"Unknown arguments for {tool['name']}: {', '.join(unknown)} (accepted: {allowed})")
    missing = [name for name in schema.get("required", []) if arguments.get(name) in (None, "")]
    if missing:
        raise ValueError(f"Missing required arguments for {tool['name']}: {', '.join(missing)}")
    values: dict[str, Any] = {}
    for name, spec in properties.items():
        if name not in arguments:
            if "default" in spec:
                values[name] = spec["default"]
            continue
        value = arguments[name]
        expected = _JSON_TYPES.get(spec.get("type", ""), (object,))
        if not isinstance(value, expected) or (spec.get("type") != "boolean" and isinstance(value, bool)):
            raise TypeError(f"Argument {name} of {tool['name']} must be a {spec.get('type')}")
        if "enum" in spec and value not in spec["enum"]:
            raise ValueError(f"Argument {name} of {tool['name']} must be one of: {', '.join(map(str, spec['enum']))}")
        values[name] = value
    return values


async def _describe_offering(contract: dict[str, Any], _: dict[str, Any]) -> dict[str, Any]:
    overview = next(
        (r.get("content") for r in contract.get("resources", []) if r.get("name") == "overview"), ""
    )
    return {
        "status": "success",
        "offering": contract["offering"],
        "overview": overview,
        "server": {"name": contract["server"]["name"], "version": contract["server"]["version"]},
        "publicAccess": contract.get("publicAccess", {}),
        "tools": [tool["name"] for tool in contract.get("tools", [])],
    }


def _resource_data(contract: dict[str, Any], name: str) -> Any:
    return next((r.get("data") for r in contract.get("resources", []) if r.get("name") == name), None)


async def _list_public_capabilities(contract: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    surface = args.get("surface", "all")
    apis = _resource_data(contract, "public-apis") or {}
    surfaces = {
        "python-api": apis.get("pythonApis", []),
        "mcp-tools": [tool["name"] for tool in contract.get("tools", [])],
        "cli": apis.get("cli", []),
        "browser-docs": apis.get("docs", []),
    }
    capabilities = surfaces if surface == "all" else {surface: surfaces[surface]}
    return {"status": "success", "surface": surface, "capabilities": capabilities}


def _matches(text: str, words: set[str]) -> int:
    return sum(1 for word in re.findall(r"[a-z]+", text.lower()) if word in words)


async def _map_workflow_to_tools(contract: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    words = {word for word in re.findall(r"[a-z]+", args["workflow"].lower()) if len(word) > 3}
    workflows = _resource_data(contract, "workflows") or []
    ranked = sorted(
        workflows,
        key=lambda item: _matches(f"{item.get('id', '')} {item.get('goal', '')}", words),
        reverse=True,
    )
    best = [w for w in ranked if _matches(f"{w.get('id', '')} {w.get('goal', '')}", words)]
    return {
        "status": "success",
        "workflows": best or workflows,
        "matched": bool(best),
        "approvalRules": (_resource_data(contract, "security-and-audit") or {}).get(
            "humanApprovalRequiredFor", []
        ),
    }


async def _operate_browser_docs(contract: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    access = contract.get("publicAccess", {})
    return {
        "status": "success",
        "task": "Use public pages only; do not sign in or open provider dashboards without approval.",
        "publicPages": {
            "docs": access.get("docsUrl"),
            "pypi": access.get("pypiUrl"),
            "repository": access.get("repositoryUrl"),
        },
        "browserAutomation": access.get("browserAutomation", {}),
    }


async def _prepare_provider_setup(service: str, provider: str, project_type: str) -> dict[str, Any]:
    setup = await _setup_quickstart(service, provider, project_type)
    if setup.get("status") == "success":
        info = await _get_provider_info(service, provider)
        if info.get("status") == "success":
            setup["provider_info"] = info["info"]
    return setup


ToolHandler = Callable[[dict[str, Any], dict[str, Any]], Awaitable[dict[str, Any]]]

# Contract tool name -> handler(contract, validated arguments).
TOOL_HANDLERS: dict[str, ToolHandler] = {
    "describe_offering": _describe_offering,
    "list_public_capabilities": _list_public_capabilities,
    "map_workflow_to_tools": _map_workflow_to_tools,
    "operate_browser_docs": _operate_browser_docs,
    "prepare_provider_setup": lambda c, a: _prepare_provider_setup(
        a["service"], a["provider"], a.get("projectType", "existing")
    ),
    "plan_provider_migration": lambda c, a: _get_migration_guide(
        a["service"], a["fromProvider"], a["toProvider"]
    ),
    "explain": lambda c, a: _explain(a["topic"]),
    "compare_providers": lambda c, a: _compare_providers(a["service"], a.get("useCase", "")),
    "troubleshoot": lambda c, a: _troubleshoot(a["scenario"], a.get("errorMessage", "")),
    "list_providers": lambda c, a: _list_providers(a["service"]),
    "get_provider_info": lambda c, a: _get_provider_info(a["service"], a["provider"]),
    "generate_code": lambda c, a: _generate_code(
        a["service"], a["operation"], a.get("context", "")
    ),
    "get_usage_examples": lambda c, a: _get_usage_examples(a["service"], a.get("pattern", "")),
    "get_config": lambda c, a: _get_config(a.get("service", "all")),
    "send_test_email": lambda c, a: _send_test_email(a["to"], a["subject"], a["body"]),
    "send_test_sms": lambda c, a: _send_test_sms(a["to"], a["message"]),
    "check_storage": lambda c, a: _check_storage(a.get("testUpload", False)),
}


def _find_tool(contract: dict[str, Any], name: str) -> dict[str, Any]:
    for tool in contract.get("tools", []):
        if tool.get("name") == name:
            return cast(dict[str, Any], tool)
    raise KeyError(name)


async def call_tool_async(
    contract: dict[str, Any], name: str, arguments: Mapping[str, Any]
) -> dict[str, Any]:
    """Run one contract tool and return an MCP ``CallToolResult`` as a dict."""
    tool = _find_tool(contract, name)
    values = _validated_arguments(tool, arguments)
    try:
        payload = await TOOL_HANDLERS[name](contract, values)
    except Exception as exc:  # report the failure without raw exception text
        payload = {
            "status": "error",
            "message": "Tool execution failed; inspect local provider configuration",
            "error_type": type(exc).__name__,
        }
    return {
        "content": [{"type": "text", "text": pretty_json(payload)}],
        "structuredContent": payload,
        "isError": payload.get("status") == "error",
    }


def call_tool(contract: dict[str, Any], name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
    return asyncio.run(call_tool_async(contract, name, arguments))


# ---------------------------------------------------------------------------
# stdio server
# ---------------------------------------------------------------------------


def handle(message: object, contract: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(message, Mapping):
        return error(None, -32600, "Invalid Request")
    is_notification = "id" not in message
    request_id = message.get("id")
    method = message.get("method")
    if not is_notification and (
        isinstance(request_id, bool) or not isinstance(request_id, str | int)
    ):
        return error(None, -32600, "Invalid Request")
    if message.get("jsonrpc") != "2.0":
        return None if is_notification else error(request_id, -32600, "Invalid Request")
    if not isinstance(method, str) or not method:
        return None if is_notification else error(request_id, -32600, "Invalid Request")
    raw_params = message.get("params", {})
    if raw_params is None:
        raw_params = {}
    if not isinstance(raw_params, Mapping):
        return None if is_notification else error(request_id, -32602, "Invalid params")
    params = cast(Mapping[str, Any], raw_params)

    try:
        if method == "initialize":
            response = result(
                request_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {
                        "resources": {"listChanged": False},
                        "tools": {"listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": contract["server"]["name"],
                        "title": contract["server"].get("title", contract["offering"]["name"]),
                        "version": contract["server"]["version"],
                    },
                    "instructions": contract.get("instructions", ""),
                },
            )
        elif method == "ping":
            response = result(request_id, {})
        elif method == "resources/list":
            response = result(request_id, list_resources(contract))
        elif method == "resources/read":
            uri = params["uri"]
            if not isinstance(uri, str):
                raise TypeError("uri must be a string")
            response = result(request_id, read_resource(contract, uri))
        elif method == "tools/list":
            response = result(request_id, list_tools(contract))
        elif method == "tools/call":
            name = params["name"]
            arguments = params.get("arguments", {})
            if arguments is None:
                arguments = {}
            if not isinstance(name, str) or not isinstance(arguments, Mapping):
                raise TypeError("tool name and arguments have invalid types")
            response = result(request_id, call_tool(contract, name, dict(arguments)))
        elif method == "prompts/list":
            response = result(request_id, list_prompts(contract))
        elif method == "prompts/get":
            name = params["name"]
            arguments = params.get("arguments", {})
            if arguments is None:
                arguments = {}
            if not isinstance(name, str) or not isinstance(arguments, Mapping):
                raise TypeError("prompt name and arguments have invalid types")
            response = result(request_id, get_prompt(contract, name, dict(arguments)))
        else:
            response = error(request_id, -32601, f"Method not found: {_shorten(method)}")
    except (KeyError, TypeError, ValueError) as exc:
        response = error(request_id, -32602, f"Unknown or invalid parameter: {_shorten(exc)}")
    except Exception as exc:  # pragma: no cover - defensive protocol boundary
        response = error(request_id, -32603, "Internal error", {"detail": type(exc).__name__})
    return None if is_notification else response


def main() -> None:
    """Run the SwapLayer MCP server over stdio (``swaplayer-mcp``)."""
    contract = load_contract()
    if isinstance(sys.stdin, io.TextIOWrapper):
        # MCP stdio is UTF-8 whatever the locale; parse_message rejects undecodable bytes.
        sys.stdin.reconfigure(encoding="utf-8", errors="surrogateescape")
    while True:
        line = sys.stdin.readline(MAX_MESSAGE_CHARS + 1)
        if not line:
            break
        if len(line) > MAX_MESSAGE_CHARS:
            while line and not line.endswith("\n"):
                line = sys.stdin.readline(MAX_MESSAGE_CHARS + 1)
            write_message(error(None, -32700, "Message exceeds the size limit"))
            continue
        if not line.strip():
            continue
        try:
            message = parse_message(line)
        except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as exc:
            write_message(error(None, -32700, "Parse error", {"detail": _shorten(exc)}))
            continue
        response = handle(message, contract)
        if response is not None:
            write_message(response)


def create_mcp_server() -> Any:
    """
    Build an MCP SDK server that serves the same contract, tools and prompts.

    Use this to embed SwapLayer's MCP server in your own process. It needs the
    MCP SDK: ``pip install "SwapLayer[mcp]"``. The ``swaplayer-mcp`` command
    does not.
    """
    try:
        import mcp.types as types

        from mcp.server import Server
    except ImportError as exc:
        raise ImportError(
            'create_mcp_server() needs the MCP SDK. Install with: pip install "SwapLayer[mcp]"'
        ) from exc
    from mcp.server.lowlevel.helper_types import ReadResourceContents

    contract = load_contract()
    server = Server(
        contract["server"]["name"],
        version=contract["server"]["version"],
        instructions=contract.get("instructions"),
    )

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=tool["name"],
                title=tool["title"],
                description=tool["description"],
                inputSchema=tool["inputSchema"],
                annotations=types.ToolAnnotations(**tool["annotations"]),
            )
            for tool in list_tools(contract)["tools"]
        ]

    @server.call_tool(validate_input=False)
    async def _call_tool(name: str, arguments: dict[str, Any] | None) -> types.CallToolResult:
        outcome = await call_tool_async(contract, name, arguments or {})
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=outcome["content"][0]["text"])],
            structuredContent=outcome["structuredContent"],
            isError=outcome["isError"],
        )

    @server.list_resources()
    async def _list_resources() -> list[types.Resource]:
        return [types.Resource(**item) for item in list_resources(contract)["resources"]]

    @server.read_resource()
    async def _read_resource(uri: Any) -> list[ReadResourceContents]:
        contents = read_resource(contract, str(uri))["contents"]
        return [ReadResourceContents(content=item["text"], mime_type=item["mimeType"]) for item in contents]

    @server.list_prompts()
    async def _list_prompts() -> list[types.Prompt]:
        return [
            types.Prompt(
                name=prompt["name"],
                title=prompt["title"],
                description=prompt["description"],
                arguments=[types.PromptArgument(**argument) for argument in prompt["arguments"]],
            )
            for prompt in list_prompts(contract)["prompts"]
        ]

    @server.get_prompt()
    async def _get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
        prompt = get_prompt(contract, name, dict(arguments or {}))
        return types.GetPromptResult(
            description=prompt["description"],
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(type="text", text=message["content"]["text"]),
                )
                for message in prompt["messages"]
            ],
        )

    return server


# ---------------------------------------------------------------------------
# Runtime tool implementations
# ---------------------------------------------------------------------------


async def _get_config(service: str) -> dict[str, Any]:
    """Get SwapLayer configuration."""
    from swap_layer.settings import get_swaplayer_settings

    try:
        settings = get_swaplayer_settings()

        communications = settings.communications
        services = {
            "billing": settings.billing,
            "email": communications.email if communications else None,
            "sms": communications.sms if communications else None,
            "storage": settings.storage,
            "identity": settings.identity,
            "verification": settings.verification,
        }
        if service == "all":
            return {"status": "success", "config": {
                key: _redact_config(value) for key, value in services.items() if value is not None
            }}
        if service not in services:
            return {"status": "error", "message": "Unknown service"}
        if services[service] is not None:
            return {"status": "success", "service": service, "config": _redact_config(services[service])}
        return {"status": "not_configured", "service": service}
    except Exception as e:
        return {"status": "error", "message": "Configuration could not be loaded", "error_type": type(e).__name__}


async def _list_providers(service: str) -> dict[str, Any]:
    """List available providers for a service."""
    providers = {
        "email": ["django", "smtp"],
        "billing": ["stripe", "paypal", "square"],
        "sms": ["twilio", "sns"],
        "storage": ["local", "django", "gcs"],
        "identity": ["workos", "auth0"],
        "verification": ["stripe"],
    }

    if service not in providers:
        return {"status": "error", "message": f"Unknown service: {service}"}

    return {"status": "success", "service": service, "providers": providers[service]}


async def _send_test_email(to: str, subject: str, body: str) -> dict[str, Any]:
    """Send a test email."""
    try:
        from swap_layer import get_provider

        email_provider = get_provider("email")
        result = email_provider.send_email(to=[to], subject=subject, text_body=body)

        return {"status": "success", "message": "Test email sent successfully", "result": result}
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to send test email; inspect local provider configuration",
            "error_type": type(e).__name__,
        }


async def _send_test_sms(to: str, message: str) -> dict[str, Any]:
    """Send a test SMS."""
    try:
        from swap_layer import get_provider

        sms_provider = get_provider("sms")
        result = sms_provider.send_sms(to=to, message=message)

        return {"status": "success", "message": "Test SMS sent successfully", "result": result}
    except Exception as e:
        return {
            "status": "error",
            "message": "Failed to send test SMS; inspect local provider configuration",
            "error_type": type(e).__name__,
        }


async def _check_storage(test_upload: bool = False) -> dict[str, Any]:
    """Check storage provider configuration."""
    try:
        from swap_layer import get_provider

        storage_provider = get_provider("storage")

        info = {
            "status": "success",
            "message": "Storage provider configured",
            "provider_type": type(storage_provider).__name__,
        }

        if test_upload:
            test_content = b"SwapLayer MCP test file"
            # A dedicated prefix keeps the probe away from application files.
            test_filename = f"{STORAGE_CHECK_PREFIX}{uuid.uuid4().hex}.txt"
            uploaded = False
            try:
                storage_provider.upload_file(test_filename, BytesIO(test_content))
                uploaded = True
                info["test_upload"] = "success"
            except Exception as e:
                info["test_upload"] = "failed"
                info["test_error"] = type(e).__name__
            if uploaded:
                try:
                    storage_provider.delete_file(test_filename)
                    info["test_cleanup"] = "deleted"
                except Exception as e:
                    info["test_cleanup"] = "failed"
                    info["test_cleanup_error"] = type(e).__name__
                    info["test_file"] = test_filename

        return info
    except Exception as e:
        return {
            "status": "error",
            "message": "Storage check failed; inspect local provider configuration",
            "error_type": type(e).__name__,
        }


async def _get_provider_info(service: str, provider: str) -> dict[str, Any]:
    """Get information about a specific provider."""
    provider_info = _GUIDANCE["info"]

    if service not in provider_info:
        return {"status": "error", "message": f"Unknown service: {service}"}

    if provider not in provider_info[service]:
        return {
            "status": "error",
            "message": f"Unknown provider '{provider}' for service '{service}'",
        }

    return {
        "status": "success",
        "service": service,
        "provider": provider,
        "info": provider_info[service][provider],
    }


async def _generate_code(service: str, operation: str, context: str = "") -> dict[str, Any]:
    """Return a code example for using SwapLayer; nothing is executed."""
    code_templates = _GUIDANCE["code"]

    if service in code_templates and operation in code_templates[service]:
        code = code_templates[service][operation]
        return {
            "status": "success",
            "service": service,
            "operation": operation,
            "code": code,
            "language": "python",
        }

    generic_templates = {
        "email": "send_email",
        "billing": "create_customer",
        "sms": "send_sms",
        "storage": "upload_file",
        "identity": "oauth_flow",
        "verification": "create_verification",
    }

    if service in generic_templates:
        default_op = generic_templates[service]
        code = code_templates[service][default_op]
        return {
            "status": "success",
            "service": service,
            "operation": f"{operation} (showing default example: {default_op})",
            "code": code,
            "language": "python",
            "note": f"Specific operation '{operation}' not found. Showing common example.",
        }

    return {"status": "error", "message": f"No code templates available for service '{service}'"}


async def _get_usage_examples(service: str, pattern: str = "") -> dict[str, Any]:
    """Get common usage examples and patterns."""
    examples = _GUIDANCE["examples"]

    if service not in examples:
        return {"status": "error", "message": f"No examples available for service '{service}'"}

    if pattern and pattern in examples[service]:
        example = examples[service][pattern]
        return {
            "status": "success",
            "service": service,
            "pattern": pattern,
            "description": example["description"],
            "code": example["code"],
            "language": "python",
        }

    return {
        "status": "success",
        "service": service,
        "patterns": [
            {"name": name, "description": data["description"], "code": data["code"]}
            for name, data in examples[service].items()
        ],
    }


async def _setup_quickstart(
    service: str, provider: str, project_type: str = "existing"
) -> dict[str, Any]:
    """Generate complete quickstart configuration for SwapLayer."""
    quickstart_configs = _GUIDANCE["quickstarts"]

    if service not in quickstart_configs:
        return {"status": "error", "message": f"Quickstart not available for service '{service}'"}

    if provider not in quickstart_configs[service]:
        available_providers = list(quickstart_configs[service].keys())
        return {
            "status": "error",
            "message": f"Quickstart not available for provider '{provider}' in service '{service}'",
            "available_providers": available_providers,
        }

    config = quickstart_configs[service][provider]

    setup_steps = [
        f"1. Install SwapLayer with {service} support:",
        f"   {config['pip_install']}",
        "",
        "2. Add configuration to Django settings.py or call configure(SWAPLAYER) in your Python process:",
        config["settings_config"],
        "",
        "3. Set up environment variables (recommended for production):",
        config["env_vars"],
        "",
        "4. Get your credentials:",
        f"   {config['credentials_instructions']}",
        "",
        "5. Start using SwapLayer:",
        config["usage_example"],
    ]

    if project_type == "new":
        setup_steps.insert(0, "0. Create an isolated Python environment; use a Django project for email/OAuth adapters:")
        setup_steps.insert(1, "   python -m venv .venv")
        setup_steps.insert(2, "   Activate the environment before installing extras.")
        setup_steps.insert(3, "")

    return {
        "status": "success",
        "service": service,
        "provider": provider,
        "project_type": project_type,
        "quickstart": "\n".join(setup_steps),
        "pip_install": config["pip_install"],
        "settings_config": config["settings_config"],
        "env_vars": config["env_vars"],
        "usage_example": config["usage_example"],
        "credentials_instructions": config["credentials_instructions"],
    }


# explain() topic -> tools that usually come next.
_RELATED_TOOLS: dict[str, list[str]] = {
    "overview": ["list_providers", "compare_providers"],
    "docs-index": ["explain"],
    "philosophy": ["plan_provider_migration"],
    "architecture": ["get_provider_info"],
    "billing": ["prepare_provider_setup", "generate_code"],
    "email": ["prepare_provider_setup", "send_test_email"],
    "sms": ["prepare_provider_setup", "send_test_sms"],
    "storage": ["prepare_provider_setup", "check_storage"],
    "identity-platform": ["prepare_provider_setup", "generate_code"],
    "identity-verification": ["prepare_provider_setup", "generate_code"],
    "mcp": ["get_config", "describe_offering"],
    "security": ["get_config"],
    "faq": ["troubleshoot"],
}


async def _explain(topic: str) -> dict[str, Any]:
    """Explain a SwapLayer concept."""
    if topic not in _EXPLAIN_TOPICS:
        available = list(_EXPLAIN_TOPICS.keys())
        return {
            "status": "error",
            "message": f"Unknown topic '{topic}'",
            "available_topics": available,
        }

    return {
        "status": "success",
        "topic": topic,
        "content": _EXPLAIN_TOPICS[topic],
        "format": "markdown",
        "related_tools": _RELATED_TOOLS.get(topic, []),
    }


async def _compare_providers(service: str, use_case: str = "") -> dict[str, Any]:
    """Compare providers for a service."""
    if service not in _PROVIDER_COMPARISONS:
        return {"status": "error", "message": f"No comparison data for service '{service}'"}

    comparison = _PROVIDER_COMPARISONS[service]
    result: dict[str, Any] = {
        "status": "success",
        "service": service,
        "summary": comparison["summary"],
        "providers": comparison["providers"],
        "decision_guide": comparison["decision_guide"],
    }

    # If a use case is given, try to highlight the best match
    if use_case:
        use_case_lower = use_case.lower()
        scored: list[tuple[str, int]] = []
        for provider_name, info in comparison["providers"].items():
            score = 0
            text = f"{info['best_for']} {' '.join(info['pros'])} {info.get('recommended_when', '')}".lower()
            for word in use_case_lower.split():
                if word in text:
                    score += 1
            scored.append((provider_name, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        if scored and scored[0][1] > 0:
            result["recommended_for_use_case"] = scored[0][0]
            result["use_case_analysis"] = (
                f"'{scored[0][0]}' matches the stated use case best. "
                f"See its 'recommended_when' field for confirmation."
            )

    return result


async def _troubleshoot(scenario: str, error_message: str = "") -> dict[str, Any]:
    """Diagnose a SwapLayer configuration issue."""
    if scenario not in _TROUBLESHOOT_SCENARIOS:
        available = list(_TROUBLESHOOT_SCENARIOS.keys())
        return {
            "status": "error",
            "message": f"Unknown scenario '{scenario}'",
            "available_scenarios": available,
        }

    info = _TROUBLESHOOT_SCENARIOS[scenario]
    result: dict[str, Any] = {
        "status": "success",
        "scenario": scenario,
        "symptoms": info["symptoms"],
        "cause": info["cause"],
        "solution": info["solution"],
    }

    if error_message:
        # Match the error to a known symptom; the caller's text is never echoed back.
        for symptom in info["symptoms"]:
            if any(word in error_message for word in symptom.split()):
                result["symptom_matched"] = symptom
                break

    return result


async def _get_migration_guide(
    service: str, from_provider: str, to_provider: str
) -> dict[str, Any]:
    """Generate a provider migration guide."""
    valid_providers = {
        "email": ["django", "smtp", "sendgrid", "mailgun", "ses"],
        "billing": ["stripe", "paypal", "square"],
        "sms": ["twilio", "sns"],
        "storage": ["local", "django", "s3", "azure", "gcs"],
        "identity": ["workos", "auth0"],
        "verification": ["stripe"],
    }

    if service not in valid_providers:
        return {"status": "error", "message": f"Unknown service: {service}"}

    known = valid_providers[service]
    warnings = []
    if from_provider not in known:
        warnings.append(
            f"'{from_provider}' is not a recognised provider for {service}. Known: {known}"
        )
    if to_provider not in known:
        warnings.append(
            f"'{to_provider}' is not a recognised provider for {service}. Known: {known}"
        )

    # Data migration notes by service
    data_notes: dict[str, str] = {
        "billing": (
            "Customer IDs and subscription IDs are provider-specific. "
            "You will need to migrate customers and subscriptions to the new provider, "
            "or maintain both providers during a transition period. "
            "Review application code and provider capabilities as well: "
            "any stored customer_id / subscription_id values in your database are "
            "provider-specific and must be re-mapped."
        ),
        "email": (
            "No data migration required. "
            "Suppression lists (unsubscribes) are provider-specific — "
            "export them from your current provider and import into the new one."
        ),
        "sms": (
            "No data migration required. "
            "Opt-out lists are provider-specific — ensure you honour existing opt-outs "
            "by importing them into the new provider before sending."
        ),
        "storage": (
            "Files are stored in the old provider's bucket/container. "
            "You must either: (a) copy all files to the new provider, "
            "or (b) run both providers simultaneously during a migration window. "
            "File URLs stored in your database will change."
        ),
        "identity": (
            "User sessions managed by the old provider will be invalidated. "
            "Users will need to log in again after migration. "
            "Directory sync / SCIM data must be re-configured with the new provider."
        ),
        "verification": (
            "Only Stripe Identity is implemented. Application records, in-progress sessions, retention and authorization require review; the library does not migrate them."
        ),
    }

    steps = [
        f"## Migration: {service} from {from_provider} to {to_provider}",
        "Obtain a current target-provider setup with prepare_provider_setup; some names are Django backend choices.",
        "Install the required extra and configure a non-production caller-owned account.",
        "Review adapter capability differences, application calls, webhook signatures, IDs and authorization.",
        data_notes[service],
        "Approve any test sends or writes explicitly, validate the integration and data migration, then rotate/remove old credentials.",
        "Changing a provider label alone does not migrate data or guarantee unchanged application behavior.",
    ]

    return {
        "status": "success",
        "service": service,
        "from_provider": from_provider,
        "to_provider": to_provider,
        "application_code_changes": "review-required",
        "data_migration_note": data_notes.get(service, "No data migration required."),
        "guide": "\n".join(steps),
        "warnings": warnings,
    }


if __name__ == "__main__":
    main()
