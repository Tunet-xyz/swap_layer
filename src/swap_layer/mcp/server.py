"""
MCP Server implementation for SwapLayer.

Provides tools for AI assistants to interact with SwapLayer providers,
including onboarding, documentation, and configuration tools.
"""

import json
import pathlib
import uuid
from io import BytesIO
from typing import Any

from swap_layer import __version__
from swap_layer._redaction import redact_config

try:
    import mcp.types as types

    from mcp.server import Server

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    Server = None  # type: ignore


def _redact_config(value: Any) -> Any:
    """Return configuration with every non-public field omitted, recursively."""
    return redact_config(value)

# Packaged guidance works from wheels without a source checkout or Django.
_GUIDANCE: dict[str, Any] = json.loads(pathlib.Path(__file__).with_name("guidance.json").read_text(encoding="utf-8"))

# ---------------------------------------------------------------------------
# Onboarding knowledge base — embedded so tools work without Django or the
# docs directory being present (e.g. when SwapLayer is installed as a package)
# ---------------------------------------------------------------------------

_EXPLAIN_TOPICS: dict[str, str] = _GUIDANCE['explain']

_PROVIDER_COMPARISONS: dict[str, Any] = _GUIDANCE['comparisons']

_TROUBLESHOOT_SCENARIOS: dict[str, Any] = _GUIDANCE['troubleshoot']


def create_mcp_server() -> Any:
    """
    Create and configure the SwapLayer MCP server.

    Returns:
        Configured MCP Server instance

    Raises:
        ImportError: If mcp package is not installed
    """
    if not MCP_AVAILABLE:
        raise ImportError(
            "MCP server requires 'mcp' package. Install with: pip install 'SwapLayer[mcp]'"
        )

    server = Server("swaplayer", version=__version__, instructions="Local caller-owned tools. Obtain approval before test sends or storage writes; use test accounts. No maintainer agent or token is available.")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        """List available SwapLayer tools."""
        tools = [
            # ── Operational tools (require configured Django + providers) ──────
            types.Tool(
                name="swaplayer_get_config",
                description="Get current SwapLayer configuration for a specific service or all services",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service type (email, payments, sms, storage, identity, verification) or 'all' for all services",
                            "enum": [
                                "all",
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        }
                    },
                    "required": ["service"],
                },
            ),
            types.Tool(
                name="swaplayer_list_providers",
                description="List available providers for a specific service type",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service type to list providers for",
                            "enum": [
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        }
                    },
                    "required": ["service"],
                },
            ),
            types.Tool(
                name="swaplayer_send_test_email",
                description="Send a test email using the configured email provider",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email address"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body (plain text)"},
                    },
                    "required": ["to", "subject", "body"],
                },
            ),
            types.Tool(
                name="swaplayer_send_test_sms",
                description="Send a test SMS using the configured SMS provider",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient phone number (E.164 format)",
                        },
                        "message": {"type": "string", "description": "SMS message text"},
                    },
                    "required": ["to", "message"],
                },
            ),
            types.Tool(
                name="swaplayer_check_storage",
                description="Check storage provider configuration and test connectivity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "test_upload": {
                            "type": "boolean",
                            "description": "Whether to perform a test file upload/delete",
                            "default": False,
                        }
                    },
                },
            ),
            types.Tool(
                name="swaplayer_get_provider_info",
                description="Get detailed information about a specific provider implementation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service type",
                            "enum": [
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        },
                        "provider": {
                            "type": "string",
                            "description": "Provider name (e.g., 'stripe', 'sendgrid', 'twilio')",
                        },
                    },
                    "required": ["service", "provider"],
                },
            ),
            types.Tool(
                name="swaplayer_generate_code",
                description="Generate code examples for using SwapLayer with specific operations and services",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service type to generate code for",
                            "enum": [
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        },
                        "operation": {
                            "type": "string",
                            "description": "Operation to perform (e.g., 'send_email', 'create_customer', 'upload_file')",
                        },
                        "context": {
                            "type": "string",
                            "description": "Optional context about the use case or requirements",
                        },
                    },
                    "required": ["service", "operation"],
                },
            ),
            types.Tool(
                name="swaplayer_get_usage_examples",
                description="Get common usage examples and patterns for a specific service",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service type to get examples for",
                            "enum": [
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Specific pattern or use case (e.g., 'welcome_email', 'subscription_flow', 'file_upload')",
                        },
                    },
                    "required": ["service"],
                },
            ),
            types.Tool(
                name="swaplayer_setup_quickstart",
                description="Generate complete quickstart configuration and setup code for SwapLayer with a specific service and provider. Returns Django settings configuration and installation instructions.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service type to set up",
                            "enum": [
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        },
                        "provider": {
                            "type": "string",
                            "description": "Provider to use (e.g., 'stripe', 'sendgrid', 'twilio', 's3')",
                        },
                        "project_type": {
                            "type": "string",
                            "description": "Type of Django project setup",
                            "enum": ["new", "existing"],
                            "default": "existing",
                        },
                    },
                    "required": ["service", "provider"],
                },
            ),
            # ── Onboarding tools (no Django / configured providers required) ───
            types.Tool(
                name="swaplayer_explain",
                description=(
                    "Explain SwapLayer concepts for onboarding. "
                    "Works without any Django project configured. "
                    "Use this first to understand what SwapLayer is and how it works."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Concept to explain",
                            "enum": [
                                "overview",
                                "philosophy",
                                "architecture",
                                "installation",
                                "django-integration",
                                "security",
                                "providers",
                                "faq",
                            ],
                        }
                    },
                    "required": ["topic"],
                },
            ),
            types.Tool(
                name="swaplayer_compare_providers",
                description=(
                    "Compare available providers for a SwapLayer service to help choose the right one. "
                    "Returns a decision guide with pros, cons, and recommendations. "
                    "Works without any Django project configured."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service to compare providers for",
                            "enum": [
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        },
                        "use_case": {
                            "type": "string",
                            "description": "Optional: describe your use case to get a more targeted recommendation (e.g. 'high-volume transactional email', 'SaaS subscriptions', 'EU data residency required')",
                        },
                    },
                    "required": ["service"],
                },
            ),
            types.Tool(
                name="swaplayer_troubleshoot",
                description=(
                    "Diagnose and resolve common SwapLayer configuration issues. "
                    "Provide an error message or symptom to get a targeted solution."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "scenario": {
                            "type": "string",
                            "description": "Known issue category",
                            "enum": [
                                "missing_config",
                                "missing_package",
                                "invalid_credentials",
                                "wrong_provider_name",
                                "django_not_setup",
                                "mcp_not_installed",
                            ],
                        },
                        "error_message": {
                            "type": "string",
                            "description": "Optional: paste the actual error message to get more context",
                        },
                    },
                    "required": ["scenario"],
                },
            ),
            types.Tool(
                name="swaplayer_get_migration_guide",
                description=(
                    "Get a step-by-step guide for migrating from one SwapLayer provider to another. "
                    "Shows exactly what configuration changes to make and confirms that application "
                    "code does NOT need to change."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service to migrate",
                            "enum": [
                                "email",
                                "payments",
                                "sms",
                                "storage",
                                "identity",
                                "verification",
                            ],
                        },
                        "from_provider": {
                            "type": "string",
                            "description": "Current provider (e.g., 'stripe', 'sendgrid', 'twilio')",
                        },
                        "to_provider": {
                            "type": "string",
                            "description": "Target provider to migrate to",
                        },
                    },
                    "required": ["service", "from_provider", "to_provider"],
                },
            ),
        ]
        for tool in tools:
            tool.annotations = types.ToolAnnotations(
                readOnlyHint=tool.name not in {"swaplayer_send_test_email", "swaplayer_send_test_sms", "swaplayer_check_storage"},
                openWorldHint=tool.name in {"swaplayer_send_test_email", "swaplayer_send_test_sms", "swaplayer_check_storage"},
            )
        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: Any) -> list[types.TextContent]:
        """Handle tool calls."""
        try:
            if name == "swaplayer_get_config":
                result = await _get_config(arguments.get("service", "all"))
            elif name == "swaplayer_list_providers":
                result = await _list_providers(arguments["service"])
            elif name == "swaplayer_send_test_email":
                result = await _send_test_email(
                    arguments["to"], arguments["subject"], arguments["body"]
                )
            elif name == "swaplayer_send_test_sms":
                result = await _send_test_sms(arguments["to"], arguments["message"])
            elif name == "swaplayer_check_storage":
                result = await _check_storage(arguments.get("test_upload", False))
            elif name == "swaplayer_get_provider_info":
                result = await _get_provider_info(arguments["service"], arguments["provider"])
            elif name == "swaplayer_generate_code":
                result = await _generate_code(
                    arguments["service"], arguments["operation"], arguments.get("context", "")
                )
            elif name == "swaplayer_get_usage_examples":
                result = await _get_usage_examples(
                    arguments["service"], arguments.get("pattern", "")
                )
            elif name == "swaplayer_setup_quickstart":
                result = await _setup_quickstart(
                    arguments["service"],
                    arguments["provider"],
                    arguments.get("project_type", "existing"),
                )
            elif name == "swaplayer_explain":
                result = await _explain(arguments["topic"])
            elif name == "swaplayer_compare_providers":
                result = await _compare_providers(
                    arguments["service"], arguments.get("use_case", "")
                )
            elif name == "swaplayer_troubleshoot":
                result = await _troubleshoot(
                    arguments["scenario"], arguments.get("error_message", "")
                )
            elif name == "swaplayer_get_migration_guide":
                result = await _get_migration_guide(
                    arguments["service"],
                    arguments["from_provider"],
                    arguments["to_provider"],
                )
            else:
                raise ValueError(f"Unknown tool: {name}")

            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            error_result = {"error": "Tool execution failed; inspect local provider configuration", "type": type(e).__name__}
            return [types.TextContent(type="text", text=json.dumps(error_result, indent=2))]

    # ── Resources — expose documentation for agents to read directly ──────────

    @server.list_resources()
    async def list_resources() -> list[types.Resource]:
        """List SwapLayer documentation resources."""
        resources = [
            types.Resource(
                uri="swaplayer://docs/overview",
                name="SwapLayer Overview",
                description="What SwapLayer is, what problems it solves, and the core API",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/architecture",
                name="Architecture Guide",
                description="Provider adapter pattern, service structure, and design decisions",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/email",
                name="Email Service Guide",
                description="Email providers, configuration, and usage examples",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/billing",
                name="Billing & Payments Guide",
                description="Payment providers, subscriptions, customers, and billing flows",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/sms",
                name="SMS Service Guide",
                description="SMS providers, configuration, and usage examples",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/storage",
                name="File Storage Guide",
                description="Storage providers, file upload/download, and URL generation",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/identity-platform",
                name="Identity Platform Guide",
                description="OAuth / SSO authentication providers",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/identity-verification",
                name="Identity Verification Guide",
                description="KYC / identity verification providers",
                mimeType="text/markdown",
            ),
            types.Resource(
                uri="swaplayer://docs/mcp",
                name="MCP Server Guide",
                description="How to use SwapLayer's MCP server with AI assistants",
                mimeType="text/markdown",
            ),
        ]
        return resources

    @server.read_resource()
    async def read_resource(uri: Any) -> str:
        """Read a SwapLayer documentation resource."""
        uri_str = str(uri)

        # Map URIs to doc files
        doc_map = {
            "swaplayer://docs/overview": "README.md",
            "swaplayer://docs/architecture": "docs/architecture.md",
            "swaplayer://docs/email": "docs/email.md",
            "swaplayer://docs/billing": "docs/billing.md",
            "swaplayer://docs/sms": "docs/sms.md",
            "swaplayer://docs/storage": "docs/storage.md",
            "swaplayer://docs/identity-platform": "docs/identity-platform.md",
            "swaplayer://docs/identity-verification": "docs/identity-verification.md",
            "swaplayer://docs/mcp": "docs/mcp.md",
        }

        relative_path = doc_map.get(uri_str)
        if not relative_path:
            raise ValueError(f"Unknown resource URI: {uri_str}")

        # Try to read from the project root (works when running from source)
        doc_path = pathlib.Path(__file__).parent.parent.parent.parent / relative_path
        if doc_path.exists():
            return doc_path.read_text(encoding="utf-8")

        # Fall back to the embedded topic content for the overview
        topic_fallbacks = {
            "swaplayer://docs/overview": _EXPLAIN_TOPICS["overview"],
            "swaplayer://docs/architecture": _EXPLAIN_TOPICS["architecture"],
        }
        if uri_str in topic_fallbacks:
            return topic_fallbacks[uri_str]

        raise FileNotFoundError(
            f"Documentation file not found: {relative_path}. "
            "Run the MCP server from the SwapLayer project directory, or use "
            "swaplayer_explain / swaplayer_compare_providers tools instead."
        )

    # ── Prompts — reusable onboarding workflow templates ─────────────────────

    @server.list_prompts()
    async def list_prompts() -> list[types.Prompt]:
        """List SwapLayer onboarding prompt templates."""
        return [
            types.Prompt(
                name="onboard_service",
                description=(
                    "Walk through adding a new SwapLayer service to a Django project. "
                    "Covers installation, configuration, environment variables, and first use."
                ),
                arguments=[
                    types.PromptArgument(
                        name="service",
                        description="Service to set up (email, payments, sms, storage, identity, verification)",
                        required=True,
                    ),
                    types.PromptArgument(
                        name="provider",
                        description="Provider to use (e.g. stripe, sendgrid, twilio, s3)",
                        required=True,
                    ),
                ],
            ),
            types.Prompt(
                name="choose_provider",
                description=(
                    "Help choose the right SwapLayer provider for a service based on "
                    "requirements, budget, and infrastructure."
                ),
                arguments=[
                    types.PromptArgument(
                        name="service",
                        description="Service type (email, payments, sms, storage, identity, verification)",
                        required=True,
                    ),
                    types.PromptArgument(
                        name="requirements",
                        description="Key requirements or constraints (e.g. 'EU data residency', 'low cost', 'already on AWS')",
                        required=False,
                    ),
                ],
            ),
            types.Prompt(
                name="migrate_provider",
                description=(
                    "Guide a developer through migrating from one SwapLayer provider to another, "
                    "confirming that application code stays unchanged."
                ),
                arguments=[
                    types.PromptArgument(
                        name="service",
                        description="Service to migrate",
                        required=True,
                    ),
                    types.PromptArgument(
                        name="from_provider",
                        description="Current provider",
                        required=True,
                    ),
                    types.PromptArgument(
                        name="to_provider",
                        description="Target provider",
                        required=True,
                    ),
                ],
            ),
        ]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
        """Return a SwapLayer onboarding prompt."""
        args = arguments or {}

        if name == "onboard_service":
            service = args.get("service", "<service>")
            provider = args.get("provider", "<provider>")
            return types.GetPromptResult(
                description=f"Onboarding guide for SwapLayer {service} with {provider}",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=(
                                f"I want to add {service} support to my Django project using "
                                f"SwapLayer with the {provider} provider.\n\n"
                                f"Please:\n"
                                f"1. Call swaplayer_setup_quickstart(service='{service}', provider='{provider}') "
                                f"to get the installation and configuration steps\n"
                                f"2. Call swaplayer_generate_code(service='{service}', operation='send_{service}' "
                                f"or the most common operation) to show me a working code example\n"
                                f"3. Explain any gotchas or common mistakes to avoid\n"
                                f"4. Show me how to test it works without hitting the real API"
                            ),
                        ),
                    )
                ],
            )

        if name == "choose_provider":
            service = args.get("service", "<service>")
            requirements = args.get("requirements", "")
            requirements_text = f"\n\nMy requirements: {requirements}" if requirements else ""
            return types.GetPromptResult(
                description=f"Provider selection guide for SwapLayer {service}",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=(
                                f"I need to choose a {service} provider for my Django project "
                                f"using SwapLayer.{requirements_text}\n\n"
                                f"Please:\n"
                                f"1. Call swaplayer_compare_providers(service='{service}'"
                                + (f", use_case='{requirements}'" if requirements else "")
                                + ") to get a comparison\n"
                                "2. Recommend the best provider for my situation\n"
                                "3. Explain what I'd need to do to switch providers later if needed"
                            ),
                        ),
                    )
                ],
            )

        if name == "migrate_provider":
            service = args.get("service", "<service>")
            from_provider = args.get("from_provider", "<from>")
            to_provider = args.get("to_provider", "<to>")
            return types.GetPromptResult(
                description=f"Migration guide: {service} from {from_provider} to {to_provider}",
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(
                            type="text",
                            text=(
                                f"I want to migrate my SwapLayer {service} configuration "
                                f"from {from_provider} to {to_provider}.\n\n"
                                f"Please:\n"
                                f"1. Call swaplayer_get_migration_guide(service='{service}', "
                                f"from_provider='{from_provider}', to_provider='{to_provider}') "
                                f"for the migration steps\n"
                                f"2. Confirm which parts of my application code will need to change "
                                f"(hint: it should be zero lines of application code)\n"
                                f"3. List any data migration considerations "
                                f"(e.g. customer IDs stored in the database)"
                            ),
                        ),
                    )
                ],
            )

        raise ValueError(f"Unknown prompt: {name}")

    return server


# ---------------------------------------------------------------------------
# Existing operational tool implementations
# ---------------------------------------------------------------------------


async def _get_config(service: str) -> dict[str, Any]:
    """Get SwapLayer configuration."""
    from swap_layer.settings import get_swaplayer_settings

    try:
        settings = get_swaplayer_settings()

        communications = settings.communications
        services = {
            "payments": settings.billing,
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
        "payments": ["stripe", "paypal", "square"],
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
            test_filename = f"mcp_test_{uuid.uuid4().hex[:8]}.txt"

            try:
                storage_provider.upload_file(test_filename, BytesIO(test_content))
                storage_provider.delete_file(test_filename)
                info["test_upload"] = "success"
            except Exception as e:
                info["test_upload"] = "failed"
                info["test_error"] = type(e).__name__

        return info
    except Exception as e:
        return {
            "status": "error",
            "message": "Storage check failed; inspect local provider configuration",
            "error_type": type(e).__name__,
        }


async def _get_provider_info(service: str, provider: str) -> dict[str, Any]:
    """Get information about a specific provider."""
    provider_info = _GUIDANCE['info']

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
    """Generate code examples for using SwapLayer."""
    code_templates = _GUIDANCE['code']

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
        "payments": "create_customer",
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
    examples = _GUIDANCE['examples']

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
    quickstart_configs = _GUIDANCE['quickstarts']

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


# ---------------------------------------------------------------------------
# Onboarding tool implementations (no Django required)
# ---------------------------------------------------------------------------


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
        "related_tools": {
            "overview": ["swaplayer_list_providers", "swaplayer_compare_providers"],
            "philosophy": ["swaplayer_get_migration_guide"],
            "architecture": ["swaplayer_get_provider_info"],
            "installation": ["swaplayer_setup_quickstart"],
            "django-integration": ["swaplayer_setup_quickstart", "swaplayer_generate_code"],
            "security": ["swaplayer_get_config"],
            "providers": ["swaplayer_compare_providers", "swaplayer_setup_quickstart"],
            "faq": ["swaplayer_troubleshoot"],
        }.get(topic, []),
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
                f"Based on '{use_case}', '{scored[0][0]}' appears to be the best match. "
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
        result["error_message_provided"] = error_message
        # Try to match the error to a known symptom pattern
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
        "payments": ["stripe", "paypal", "square"],
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
        "payments": (
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
        "Obtain a current target-provider quickstart; some names are Django backend choices.",
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
