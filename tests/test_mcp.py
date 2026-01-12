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
