"""
MCP Server implementation for SwapLayer.

Provides tools for AI assistants to interact with SwapLayer providers.
"""
import json
import uuid
from typing import Any

try:
    import mcp.types as types
    from mcp.server import Server
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    Server = None  # type: ignore

# Sensitive keys that should be redacted from configuration output
SENSITIVE_KEYS = {
    'secret_key', 'api_key', 'password', 'token',
    'account_sid', 'auth_token', 'client_secret'
}


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
            types.Tool(
                name="swaplayer_generate_code",
                description="Generate code examples for using SwapLayer with specific operations and services",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service": {
                            "type": "string",
                            "description": "Service type to generate code for",
                            "enum": ["email", "payments", "sms", "storage", "identity", "verification"]
                        },
                        "operation": {
                            "type": "string",
                            "description": "Operation to perform (e.g., 'send_email', 'create_customer', 'upload_file')"
                        },
                        "context": {
                            "type": "string",
                            "description": "Optional context about the use case or requirements"
                        }
                    },
                    "required": ["service", "operation"]
                }
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
                            "enum": ["email", "payments", "sms", "storage", "identity", "verification"]
                        },
                        "pattern": {
                            "type": "string",
                            "description": "Specific pattern or use case (e.g., 'welcome_email', 'subscription_flow', 'file_upload')",
                        }
                    },
                    "required": ["service"]
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
            elif name == "swaplayer_generate_code":
                result = await _generate_code(
                    arguments["service"],
                    arguments["operation"],
                    arguments.get("context", "")
                )
            elif name == "swaplayer_get_usage_examples":
                result = await _get_usage_examples(
                    arguments["service"],
                    arguments.get("pattern", "")
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
                                     if k not in SENSITIVE_KEYS}
                        config[svc] = safe_config
            return {"status": "success", "config": config}
        else:
            # Return specific service configuration
            if hasattr(settings, service):
                svc_config = getattr(settings, service)
                if svc_config:
                    safe_config = {k: v for k, v in svc_config.items()
                                 if k not in SENSITIVE_KEYS}
                    return {"status": "success", "service": service, "config": safe_config}
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
            # Perform a test upload with unique filename to avoid conflicts
            test_content = b"SwapLayer MCP test file"
            test_filename = f"mcp_test_{uuid.uuid4().hex[:8]}.txt"

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


async def _generate_code(service: str, operation: str, context: str = "") -> dict[str, Any]:
    """Generate code examples for using SwapLayer."""
    code_templates = {
        "email": {
            "send_email": """# Send email using SwapLayer
from swap_layer import get_provider

email_provider = get_provider('email')
result = email_provider.send_email(
    to=['recipient@example.com'],
    subject='Your Subject Here',
    text_body='Plain text content',
    html_body='<h1>HTML content</h1>',  # optional
    from_email='sender@example.com'  # optional, uses default
)
print(f"Email sent: {{result['message_id']}}")""",
            "send_with_attachment": """# Send email with attachment
from swap_layer import get_provider

email_provider = get_provider('email')
result = email_provider.send_email(
    to=['recipient@example.com'],
    subject='Document Attached',
    text_body='Please find the attached document.',
    attachments=[
        {
            'filename': 'document.pdf',
            'content': open('path/to/document.pdf', 'rb').read(),
            'mimetype': 'application/pdf'
        }
    ]
)""",
        },
        "payments": {
            "create_customer": """# Create a customer
from swap_layer import get_provider

payments = get_provider('payments')
customer = payments.create_customer(
    email='customer@example.com',
    name='John Doe',
    metadata={'user_id': '12345'}
)
print(f"Customer created: {{customer['id']}}")""",
            "create_subscription": """# Create a subscription
from swap_layer import get_provider

payments = get_provider('payments')

# First create a customer
customer = payments.create_customer(email='customer@example.com')

# Then create a subscription
subscription = payments.create_subscription(
    customer_id=customer['id'],
    price_id='price_xxxxx',  # Your price ID from provider
    metadata={'plan': 'premium'}
)
print(f"Subscription created: {{subscription['id']}}")""",
            "create_payment_intent": """# Create a payment intent
from swap_layer import get_provider

payments = get_provider('payments')
intent = payments.create_payment_intent(
    amount=2000,  # Amount in cents
    currency='usd',
    customer_id='cus_xxxxx',  # optional
    metadata={'order_id': '12345'}
)
print(f"Payment intent: {{intent['id']}}")
print(f"Client secret: {{intent['client_secret']}}")""",
        },
        "sms": {
            "send_sms": """# Send SMS using SwapLayer
from swap_layer import get_provider

sms_provider = get_provider('sms')
result = sms_provider.send_sms(
    to='+15555551234',  # E.164 format
    message='Your verification code is: 123456'
)
print(f"SMS sent: {{result['message_id']}}")""",
        },
        "storage": {
            "upload_file": """# Upload file to storage
from swap_layer import get_provider

storage = get_provider('storage')

# Upload a file
with open('local_file.jpg', 'rb') as f:
    file_content = f.read()

storage.save('uploads/image.jpg', file_content)
url = storage.url('uploads/image.jpg')
print(f"File uploaded: {{url}}")""",
            "check_file_exists": """# Check if file exists
from swap_layer import get_provider

storage = get_provider('storage')

if storage.exists('uploads/image.jpg'):
    print("File exists")
    url = storage.url('uploads/image.jpg')
    print(f"URL: {{url}}")
else:
    print("File not found")""",
        },
        "identity": {
            "oauth_flow": """# OAuth authentication flow
from swap_layer import get_provider

# In your login view
identity = get_provider('identity')
auth_url = identity.get_authorization_url(
    request=request,
    redirect_uri='https://yourapp.com/callback',
    state='random_state_string'
)
return redirect(auth_url)

# In your callback view
user_data = identity.exchange_code_for_user(
    request=request,
    code=request.GET['code']
)
print(f"User logged in: {{user_data['email']}}")""",
        },
        "verification": {
            "create_verification": """# Create identity verification session
from swap_layer import get_provider

verification = get_provider('verification')
session = verification.create_verification_session(
    type='identity',
    metadata={'user_id': '12345'}
)
print(f"Verification URL: {{session['url']}}")
print(f"Session ID: {{session['id']}}")""",
        }
    }

    # Try to find the specific operation
    if service in code_templates and operation in code_templates[service]:
        code = code_templates[service][operation]
        return {
            "status": "success",
            "service": service,
            "operation": operation,
            "code": code,
            "language": "python"
        }

    # Return generic template if specific operation not found
    generic_templates = {
        "email": "send_email",
        "payments": "create_customer",
        "sms": "send_sms",
        "storage": "upload_file",
        "identity": "oauth_flow",
        "verification": "create_verification"
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
            "note": f"Specific operation '{operation}' not found. Showing common example."
        }

    return {
        "status": "error",
        "message": f"No code templates available for service '{service}'"
    }


async def _get_usage_examples(service: str, pattern: str = "") -> dict[str, Any]:
    """Get common usage examples and patterns."""
    examples = {
        "email": {
            "welcome_email": {
                "description": "Send a welcome email when user signs up",
                "code": """# Welcome email pattern
from swap_layer import get_provider

def send_welcome_email(user_email, user_name):
    email = get_provider('email')
    return email.send_email(
        to=[user_email],
        subject=f'Welcome to Our App, {user_name}!',
        html_body=f'''
            <h1>Welcome {user_name}!</h1>
            <p>Thanks for joining our platform.</p>
            <p><a href="https://yourapp.com/get-started">Get Started</a></p>
        ''',
        text_body=f'Welcome {user_name}! Thanks for joining.'
    )"""
            },
            "transactional": {
                "description": "Send transactional emails (receipts, confirmations)",
                "code": """# Transactional email pattern
from swap_layer import get_provider

def send_order_confirmation(order):
    email = get_provider('email')
    return email.send_email(
        to=[order.customer_email],
        subject=f'Order Confirmation #{order.id}',
        html_body=render_template('emails/order_confirmation.html', order=order),
        metadata={'order_id': order.id, 'type': 'order_confirmation'}
    )"""
            }
        },
        "payments": {
            "subscription_flow": {
                "description": "Complete subscription creation flow",
                "code": """# Subscription flow pattern
from swap_layer import get_provider

def create_subscription_for_user(user, plan_price_id):
    payments = get_provider('payments')

    # Create or get customer
    customer = payments.create_customer(
        email=user.email,
        name=user.name,
        metadata={'user_id': str(user.id)}
    )

    # Create subscription
    subscription = payments.create_subscription(
        customer_id=customer['id'],
        price_id=plan_price_id,
        metadata={'user_id': str(user.id)}
    )

    # Save subscription info to your database
    user.stripe_customer_id = customer['id']
    user.stripe_subscription_id = subscription['id']
    user.save()

    return subscription"""
            },
            "one_time_payment": {
                "description": "Process a one-time payment",
                "code": """# One-time payment pattern
from swap_layer import get_provider

def process_payment(amount_cents, customer_email, description):
    payments = get_provider('payments')

    # Create customer
    customer = payments.create_customer(email=customer_email)

    # Create payment intent
    intent = payments.create_payment_intent(
        amount=amount_cents,
        currency='usd',
        customer_id=customer['id'],
        metadata={'description': description}
    )

    return {
        'client_secret': intent['client_secret'],
        'payment_id': intent['id']
    }"""
            }
        },
        "sms": {
            "verification_code": {
                "description": "Send SMS verification code",
                "code": """# SMS verification pattern
from swap_layer import get_provider
import random

def send_verification_code(phone_number):
    # Generate code
    code = random.randint(100000, 999999)

    # Store code in session/cache for verification
    # session['verification_code'] = code

    # Send SMS
    sms = get_provider('sms')
    result = sms.send_sms(
        to=phone_number,
        message=f'Your verification code is: {code}'
    )

    return result"""
            }
        },
        "storage": {
            "user_upload": {
                "description": "Handle user file uploads",
                "code": """# User file upload pattern
from swap_layer import get_provider
from django.core.files.uploadedfile import UploadedFile

def handle_user_upload(uploaded_file: UploadedFile, user_id: int):
    storage = get_provider('storage')

    # Create unique filename
    import uuid
    ext = uploaded_file.name.split('.')[-1]
    filename = f'users/{user_id}/{uuid.uuid4()}.{ext}'

    # Upload to storage
    storage.save(filename, uploaded_file.read())

    # Get URL
    url = storage.url(filename)

    return {'filename': filename, 'url': url}"""
            }
        }
    }

    if service not in examples:
        return {
            "status": "error",
            "message": f"No examples available for service '{service}'"
        }

    if pattern and pattern in examples[service]:
        example = examples[service][pattern]
        return {
            "status": "success",
            "service": service,
            "pattern": pattern,
            "description": example["description"],
            "code": example["code"],
            "language": "python"
        }

    # Return all patterns for the service
    return {
        "status": "success",
        "service": service,
        "patterns": [
            {
                "name": name,
                "description": data["description"],
                "code": data["code"]
            }
            for name, data in examples[service].items()
        ]
    }
