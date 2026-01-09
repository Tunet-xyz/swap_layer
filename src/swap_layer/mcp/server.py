"""
MCP Server implementation for SwapLayer.

Provides tools for AI assistants to interact with SwapLayer providers.
"""
import json
from typing import Any

try:
    import mcp.server.stdio
    import mcp.types as types
    from mcp.server import Server
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    Server = None  # type: ignore


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
            "MCP server requires 'mcp' package. "
            "Install with: pip install 'SwapLayer[mcp]'"
        )
    
    server = Server("swaplayer")
    
    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        """List available SwapLayer tools."""
        return [
            types.Tool(
                name="swaplayer_get_config",
                description="Get current SwapLayer configuration for a specific service or all services",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service type (email, payments, sms, storage, identity, verification) or 'all' for all services",
                            "enum": ["all", "email", "payments", "sms", "storage", "identity", "verification"]
                        }
                    },
                    "required": ["service"]
                }
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
                            "enum": ["email", "payments", "sms", "storage", "identity", "verification"]
                        }
                    },
                    "required": ["service"]
                }
            ),
            types.Tool(
                name="swaplayer_send_test_email",
                description="Send a test email using the configured email provider",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email address"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject"
                        },
                        "body": {
                            "type": "string",
                            "description": "Email body (plain text)"
                        }
                    },
                    "required": ["to", "subject", "body"]
                }
            ),
            types.Tool(
                name="swaplayer_send_test_sms",
                description="Send a test SMS using the configured SMS provider",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient phone number (E.164 format)"
                        },
                        "message": {
                            "type": "string",
                            "description": "SMS message text"
                        }
                    },
                    "required": ["to", "message"]
                }
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
                            "default": False
                        }
                    }
                }
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
                            "enum": ["email", "payments", "sms", "storage", "identity", "verification"]
                        },
                        "provider": {
                            "type": "string",
                            "description": "Provider name (e.g., 'stripe', 'sendgrid', 'twilio')"
                        }
                    },
                    "required": ["service", "provider"]
                }
            ),
        ]
    
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
                    arguments["to"],
                    arguments["subject"],
                    arguments["body"]
                )
            elif name == "swaplayer_send_test_sms":
                result = await _send_test_sms(
                    arguments["to"],
                    arguments["message"]
                )
            elif name == "swaplayer_check_storage":
                result = await _check_storage(
                    arguments.get("test_upload", False)
                )
            elif name == "swaplayer_get_provider_info":
                result = await _get_provider_info(
                    arguments["service"],
                    arguments["provider"]
                )
            else:
                raise ValueError(f"Unknown tool: {name}")
            
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            error_result = {
                "error": str(e),
                "type": type(e).__name__
            }
            return [types.TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    return server


async def _get_config(service: str) -> dict[str, Any]:
    """Get SwapLayer configuration."""
    from swap_layer.settings import get_swaplayer_settings
    
    try:
        settings = get_swaplayer_settings()
        
        if service == "all":
            # Return all configurations (without sensitive data)
            config = {}
            for svc in ["email", "payments", "sms", "storage", "identity", "verification"]:
                if hasattr(settings, svc):
                    svc_config = getattr(settings, svc)
                    if svc_config:
                        # Remove sensitive keys
                        safe_config = {k: v for k, v in svc_config.items() 
                                     if k not in ['secret_key', 'api_key', 'password', 'token', 
                                                'account_sid', 'auth_token', 'client_secret']}
                        config[svc] = safe_config
            return {"status": "success", "config": config}
        else:
            # Return specific service configuration
            if hasattr(settings, service):
                svc_config = getattr(settings, service)
                if svc_config:
                    safe_config = {k: v for k, v in svc_config.items() 
                                 if k not in ['secret_key', 'api_key', 'password', 'token',
                                            'account_sid', 'auth_token', 'client_secret']}
                    return {"status": "success", "service": service, "config": safe_config}
            return {"status": "not_configured", "service": service}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def _list_providers(service: str) -> dict[str, Any]:
    """List available providers for a service."""
    # Provider information based on SwapLayer's architecture
    providers = {
        "email": ["django", "smtp", "sendgrid", "mailgun", "ses"],
        "payments": ["stripe"],  # PayPal planned
        "sms": ["twilio", "sns"],
        "storage": ["django", "s3", "azure", "gcs"],
        "identity": ["workos", "auth0"],
        "verification": ["workos", "persona"]
    }
    
    if service not in providers:
        return {"status": "error", "message": f"Unknown service: {service}"}
    
    return {
        "status": "success",
        "service": service,
        "providers": providers[service]
    }


async def _send_test_email(to: str, subject: str, body: str) -> dict[str, Any]:
    """Send a test email."""
    try:
        from swap_layer import get_provider
        
        email_provider = get_provider('email')
        result = email_provider.send_email(
            to=[to],
            subject=subject,
            text_body=body
        )
        
        return {
            "status": "success",
            "message": "Test email sent successfully",
            "result": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to send test email: {str(e)}",
            "error_type": type(e).__name__
        }


async def _send_test_sms(to: str, message: str) -> dict[str, Any]:
    """Send a test SMS."""
    try:
        from swap_layer import get_provider
        
        sms_provider = get_provider('sms')
        result = sms_provider.send_sms(
            to=to,
            message=message
        )
        
        return {
            "status": "success",
            "message": "Test SMS sent successfully",
            "result": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to send test SMS: {str(e)}",
            "error_type": type(e).__name__
        }


async def _check_storage(test_upload: bool = False) -> dict[str, Any]:
    """Check storage provider configuration."""
    try:
        from swap_layer import get_provider
        
        storage_provider = get_provider('storage')
        
        info = {
            "status": "success",
            "message": "Storage provider configured",
            "provider_type": type(storage_provider).__name__
        }
        
        if test_upload:
            # Perform a test upload
            test_content = b"SwapLayer MCP test file"
            test_filename = "mcp_test.txt"
            
            try:
                storage_provider.save(test_filename, test_content)
                storage_provider.delete(test_filename)
                info["test_upload"] = "success"
            except Exception as e:
                info["test_upload"] = "failed"
                info["test_error"] = str(e)
        
        return info
    except Exception as e:
        return {
            "status": "error",
            "message": f"Storage check failed: {str(e)}",
            "error_type": type(e).__name__
        }


async def _get_provider_info(service: str, provider: str) -> dict[str, Any]:
    """Get information about a specific provider."""
    # Provider documentation and capabilities
    provider_info = {
        "email": {
            "django": {
                "description": "Django's built-in email backend",
                "capabilities": ["send_email"],
                "setup": "Uses Django EMAIL_* settings"
            },
            "sendgrid": {
                "description": "SendGrid email service",
                "capabilities": ["send_email", "templates", "tracking"],
                "setup": "Requires SENDGRID_API_KEY"
            },
            "mailgun": {
                "description": "Mailgun email service",
                "capabilities": ["send_email", "templates", "tracking"],
                "setup": "Requires MAILGUN_API_KEY and domain"
            },
            "ses": {
                "description": "Amazon SES",
                "capabilities": ["send_email", "templates"],
                "setup": "Requires AWS credentials"
            }
        },
        "payments": {
            "stripe": {
                "description": "Stripe payment processing",
                "capabilities": ["customers", "subscriptions", "payment_intents", "products"],
                "setup": "Requires STRIPE_SECRET_KEY"
            }
        },
        "sms": {
            "twilio": {
                "description": "Twilio SMS service",
                "capabilities": ["send_sms"],
                "setup": "Requires TWILIO_ACCOUNT_SID and AUTH_TOKEN"
            },
            "sns": {
                "description": "Amazon SNS",
                "capabilities": ["send_sms"],
                "setup": "Requires AWS credentials"
            }
        },
        "storage": {
            "s3": {
                "description": "Amazon S3 storage",
                "capabilities": ["save", "delete", "url", "exists"],
                "setup": "Requires AWS credentials and bucket name"
            },
            "azure": {
                "description": "Azure Blob Storage",
                "capabilities": ["save", "delete", "url", "exists"],
                "setup": "Requires Azure credentials and container"
            },
            "gcs": {
                "description": "Google Cloud Storage",
                "capabilities": ["save", "delete", "url", "exists"],
                "setup": "Requires GCS credentials and bucket"
            }
        },
        "identity": {
            "workos": {
                "description": "WorkOS identity platform",
                "capabilities": ["oauth", "sso", "directory_sync"],
                "setup": "Requires WORKOS_API_KEY and CLIENT_ID"
            }
        }
    }
    
    if service not in provider_info:
        return {"status": "error", "message": f"Unknown service: {service}"}
    
    if provider not in provider_info[service]:
        return {
            "status": "error",
            "message": f"Unknown provider '{provider}' for service '{service}'"
        }
    
    return {
        "status": "success",
        "service": service,
        "provider": provider,
        "info": provider_info[service][provider]
    }
