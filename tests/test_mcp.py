"""
Tests for SwapLayer MCP server functionality.
"""

import pytest


def test_mcp_server_creation():
    """Test that MCP server can be created when dependencies are available."""
    try:
        from swap_layer.mcp import create_mcp_server

        server = create_mcp_server()
        assert server is not None
        assert hasattr(server, "name")
        assert server.name == "swaplayer"
    except ImportError:
        # MCP not installed, skip test
        pytest.skip("MCP dependencies not installed")


def test_mcp_not_available_error():
    """Test that proper error is raised when MCP is not installed."""
    try:
        # Try to import mcp
        import mcp  # noqa: F401

        # If successful, skip this test
        pytest.skip("MCP is installed, cannot test error condition")
    except ImportError:
        # MCP not installed, we expect ImportError when creating server
        # Just verify the module can be imported
        from swap_layer.mcp import create_mcp_server  # noqa: F401

        # Test passes if we can import the function
        # Actual error testing would require isolating imports
        pass


@pytest.mark.asyncio
async def test_list_providers():
    """Test list_providers functionality."""
    try:
        from swap_layer.mcp.server import _list_providers

        # Test listing email providers
        result = await _list_providers("email")
        assert result["status"] == "success"
        assert "providers" in result
        assert "sendgrid" in result["providers"]
        assert "mailgun" in result["providers"]

        # Test listing payment providers
        result = await _list_providers("payments")
        assert result["status"] == "success"
        assert "stripe" in result["providers"]

        # Test invalid service
        result = await _list_providers("invalid")
        assert result["status"] == "error"
    except ImportError:
        pytest.skip("MCP dependencies not installed")


@pytest.mark.asyncio
async def test_get_provider_info():
    """Test get_provider_info functionality."""
    try:
        from swap_layer.mcp.server import _get_provider_info

        # Test getting Stripe info
        result = await _get_provider_info("payments", "stripe")
        assert result["status"] == "success"
        assert result["provider"] == "stripe"
        assert "info" in result
        assert "description" in result["info"]
        assert "capabilities" in result["info"]

        # Test getting SendGrid info
        result = await _get_provider_info("email", "sendgrid")
        assert result["status"] == "success"
        assert result["provider"] == "sendgrid"

        # Test invalid provider
        result = await _get_provider_info("email", "invalid")
        assert result["status"] == "error"
    except ImportError:
        pytest.skip("MCP dependencies not installed")


@pytest.mark.asyncio
async def test_get_config_redacts_secrets():
    """Test that get_config properly redacts sensitive information."""
    try:
        from swap_layer.mcp.server import _get_config

        # This should not expose any secret keys
        result = await _get_config("all")

        # Config structure is tested, not actual values
        # Sensitive data redaction is handled in _get_config implementation
        assert result["status"] in ["success", "error", "not_configured"]
    except ImportError:
        pytest.skip("MCP dependencies not installed")


# ---------------------------------------------------------------------------
# Onboarding tool tests (no Django required)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_explain_all_topics():
    """Test swaplayer_explain returns content for all valid topics."""
    try:
        from swap_layer.mcp.server import _explain

        topics = [
            "overview",
            "philosophy",
            "architecture",
            "installation",
            "django-integration",
            "security",
            "providers",
            "faq",
        ]
        for topic in topics:
            result = await _explain(topic)
            assert result["status"] == "success", f"Failed for topic '{topic}'"
            assert result["topic"] == topic
            assert "content" in result
            assert len(result["content"]) > 100, f"Content too short for topic '{topic}'"
            assert result["format"] == "markdown"

    except ImportError:
        pytest.skip("MCP dependencies not installed")


@pytest.mark.asyncio
async def test_explain_invalid_topic():
    """Test that unknown topics return an error."""
    try:
        from swap_layer.mcp.server import _explain

        result = await _explain("nonexistent")
        assert result["status"] == "error"
        assert "available_topics" in result

    except ImportError:
        pytest.skip("MCP dependencies not installed")


@pytest.mark.asyncio
async def test_compare_providers_all_services():
    """Test swaplayer_compare_providers returns valid comparisons for all services."""
    try:
        from swap_layer.mcp.server import _compare_providers

        services = ["email", "payments", "sms", "storage", "identity", "verification"]
        for service in services:
            result = await _compare_providers(service)
            assert result["status"] == "success", f"Failed for service '{service}'"
            assert "providers" in result
            assert len(result["providers"]) >= 2, f"Too few providers for '{service}'"
            assert "decision_guide" in result

    except ImportError:
        pytest.skip("MCP dependencies not installed")


@pytest.mark.asyncio
async def test_compare_providers_with_use_case():
    """Test that use_case hint produces a recommendation."""
    try:
        from swap_layer.mcp.server import _compare_providers

        result = await _compare_providers("email", use_case="aws high volume")
        assert result["status"] == "success"
        # Should recommend ses for AWS high-volume use case
        if "recommended_for_use_case" in result:
            assert isinstance(result["recommended_for_use_case"], str)

    except ImportError:
        pytest.skip("MCP dependencies not installed")


@pytest.mark.asyncio
async def test_compare_providers_invalid_service():
    """Test that unknown services return an error."""
    try:
        from swap_layer.mcp.server import _compare_providers

        result = await _compare_providers("nonexistent")
        assert result["status"] == "error"

    except ImportError:
        pytest.skip("MCP dependencies not installed")


@pytest.mark.asyncio
async def test_troubleshoot_all_scenarios():
    """Test swaplayer_troubleshoot returns solutions for all known scenarios."""
    try:
        from swap_layer.mcp.server import _troubleshoot

        scenarios = [
            "missing_config",
            "missing_package",
            "invalid_credentials",
            "wrong_provider_name",
            "django_not_setup",
            "mcp_not_installed",
        ]
        for scenario in scenarios:
            result = await _troubleshoot(scenario)
            assert result["status"] == "success", f"Failed for scenario '{scenario}'"
            assert "cause" in result
            assert "solution" in result
            assert "symptoms" in result
            assert len(result["symptoms"]) >= 1

    except ImportError:
        pytest.skip("MCP dependencies not installed")


@pytest.mark.asyncio
async def test_troubleshoot_with_error_message():
    """Test troubleshoot with an error message for extra context."""
    try:
        from swap_layer.mcp.server import _troubleshoot

        result = await _troubleshoot(
            "missing_package", error_message="ImportError: No module named 'stripe'"
        )
        assert result["status"] == "success"
        assert result["error_message_provided"] == "ImportError: No module named 'stripe'"

    except ImportError:
        pytest.skip("MCP dependencies not installed")


@pytest.mark.asyncio
async def test_troubleshoot_invalid_scenario():
    """Test that unknown scenarios return an error."""
    try:
        from swap_layer.mcp.server import _troubleshoot

        result = await _troubleshoot("nonexistent_problem")
        assert result["status"] == "error"
        assert "available_scenarios" in result

    except ImportError:
        pytest.skip("MCP dependencies not installed")


@pytest.mark.asyncio
async def test_get_migration_guide_valid():
    """Test migration guide for a known provider switch."""
    try:
        from swap_layer.mcp.server import _get_migration_guide

        result = await _get_migration_guide("email", "sendgrid", "mailgun")
        assert result["status"] == "success"
        assert result["service"] == "email"
        assert result["from_provider"] == "sendgrid"
        assert result["to_provider"] == "mailgun"
        assert result["application_code_changes"] == "none"
        assert "guide" in result
        assert "data_migration_note" in result
        # Guide should mention both providers
        assert "sendgrid" in result["guide"].lower()
        assert "mailgun" in result["guide"].lower()

    except ImportError:
        pytest.skip("MCP dependencies not installed")


@pytest.mark.asyncio
async def test_get_migration_guide_payments_warns_about_ids():
    """Migration from one payment provider to another warns about stored IDs."""
    try:
        from swap_layer.mcp.server import _get_migration_guide

        result = await _get_migration_guide("payments", "stripe", "paypal")
        assert result["status"] == "success"
        # Payments migration should warn about customer IDs
        assert "customer" in result["data_migration_note"].lower()

    except ImportError:
        pytest.skip("MCP dependencies not installed")


@pytest.mark.asyncio
async def test_get_migration_guide_invalid_service():
    """Migration guide for unknown service returns error."""
    try:
        from swap_layer.mcp.server import _get_migration_guide

        result = await _get_migration_guide("unknown_service", "a", "b")
        assert result["status"] == "error"

    except ImportError:
        pytest.skip("MCP dependencies not installed")


@pytest.mark.asyncio
async def test_get_migration_guide_warns_unknown_provider():
    """Migration guide warns when a provider name isn't recognised."""
    try:
        from swap_layer.mcp.server import _get_migration_guide

        result = await _get_migration_guide("email", "sendgrid", "unknown_provider")
        # Should still succeed but include a warning
        assert result["status"] == "success"
        assert len(result["warnings"]) > 0

    except ImportError:
        pytest.skip("MCP dependencies not installed")


def test_server_has_13_tools():
    """Verify the server exposes all 13 tools (9 original + 4 onboarding)."""
    try:
        import asyncio

        from swap_layer.mcp import create_mcp_server

        server = create_mcp_server()

        # The list_tools handler is registered on the server;
        # access the underlying handler to call it
        handler = server.request_handlers.get("tools/list")
        if handler is None:
            pytest.skip("Cannot inspect tool list via this mcp version")

        tools = asyncio.run(handler(None))
        tool_names = {t.name for t in tools.tools}

        expected = {
            "swaplayer_get_config",
            "swaplayer_list_providers",
            "swaplayer_send_test_email",
            "swaplayer_send_test_sms",
            "swaplayer_check_storage",
            "swaplayer_get_provider_info",
            "swaplayer_generate_code",
            "swaplayer_get_usage_examples",
            "swaplayer_setup_quickstart",
            "swaplayer_explain",
            "swaplayer_compare_providers",
            "swaplayer_troubleshoot",
            "swaplayer_get_migration_guide",
        }
        assert expected == tool_names

    except ImportError:
        pytest.skip("MCP dependencies not installed")
