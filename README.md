# SwapLayer

SwapLayer 1.0 provides Python interfaces for billing, email, SMS, storage, and identity integrations. Configure the services you use, then call their adapters through `get_provider()`. Django supplies email, OAuth, model, and admin integrations; a small FastAPI adapter attaches configuration to application state.

Part of the [Tunet](https://www.tunet.xyz/engineering/) open-source libraries, alongside [AccessGate](https://github.com/Tunet-xyz/access_gate), [GeoCanon](https://github.com/Tunet-xyz/geo_canon), and [SessionArmor](https://github.com/Tunet-xyz/session_armor). See the [SwapLayer product page](https://www.tunet.xyz/engineering/swap-layer/) for the public capability overview.

Provider capabilities differ. Moving a provider can require data migration, webhook changes, and application changes. Unsupported operations raise errors or have documented limitations.

## Install

Python 3.10–3.13 is tested. Core dependencies are Pydantic 2, Requests, and Tenacity.

```bash
pip install 'SwapLayer==1.0.0'
pip install 'SwapLayer[stripe]==1.0.0'   # Stripe 16.x
pip install 'SwapLayer[email]==1.0.0'    # Django and django-anymail
pip install 'SwapLayer[sms]==1.0.0'      # Twilio 9.x; add [aws] for SNS
pip install 'SwapLayer[gcs]==1.0.0'      # Native Google Cloud Storage
pip install 'SwapLayer[identity]==1.0.0' # Django, WorkOS 10.x, Authlib
pip install 'SwapLayer[mcp]==1.0.0'      # Local MCP SDK 1.x
```

Other extras: `django`, `fastapi`, `paypal`, `square`, `aws`, `azure`, `all`, and `dev`. PayPal and Square use the core HTTP dependencies. Email and OAuth require configured Django settings; storage, billing, Stripe Identity, and Twilio support explicit configuration without Django.

## Start with local storage

```python
from io import BytesIO
from swap_layer import configure, get_provider

configure(storage={"provider": "local", "media_root": "./media", "media_url": "/media/"})
storage = get_provider("storage")
storage.upload_file("documents/hello.txt", BytesIO(b"hello"))
assert storage.download_file("documents/hello.txt") == b"hello"
assert storage.file_exists("documents/hello.txt")
print(storage.get_file_url("documents/hello.txt"))
```

Local URLs are plain paths; the library does not serve files or enforce URL expiry. Applications must control access to private files. Keep the local storage directory writable only by trusted application processes.

For tenant boundaries, use an explicit verified identity context:

```python
from swap_layer.storage.security import StorageSecurityContext, storage_context

context = StorageSecurityContext(
    organization_id="org-123", user_id="user-456", role="member",
    scope_format="tenants/{organization_id}",
)
with storage_context(storage, context) as scoped:
    scoped.upload_from_string("hello.txt", "tenant data")
```

This produces `tenants/org-123/hello.txt`. Contexts consume identity already verified by your application; they do not verify JWTs. System access requires `StorageSecurityContext.system_context()` explicitly.

## Configure billing

```python
import os
from swap_layer import configure, get_provider

configure(billing={"provider": "stripe", "stripe": {
    "secret_key": os.environ["STRIPE_SECRET_KEY"],
    "webhook_secret": os.environ.get("STRIPE_WEBHOOK_SECRET"),
}})
payments = get_provider("payments")
# Uses your provider account; run against a test account first.
customer = payments.create_customer(email="customer@example.com")
```

Pass integer provider minor currency units, represented by `Decimal` where required by the adapter, to payment amounts. Provider IDs, tax rules, recurring billing, and capability differences require application review. Stripe exposes the broadest catalog, usage-meter, Entitlements, and webhook administration surface.

## Current provider selection

| Service | Selectable provider values | Notes |
| --- | --- | --- |
| `email` | `django`, `smtp` | SendGrid, Mailgun, SES, and similar services use Django's Anymail backend settings. |
| `payments` | `stripe`, `paypal`, `square` | Capabilities differ; see the billing guide. |
| `sms` | `twilio`, `sns` | SNS history, delivery lookup, and balance are limited placeholders. |
| `storage` | `local`, `django`, `gcs` | S3/Azure use `django` with a configured Django storage backend. |
| `identity` | `workos`, `auth0` | Django OAuth integration; use the documented app registry. |
| `verification` | `stripe` | Stripe Identity; other verification providers are not implemented. |

Structured settings use `billing`, `communications.email`, `communications.sms`, `storage`, `identity`, and `verification`. In plain Python call `configure(...)`. In Django assign a `SwapLayerSettings` instance or dictionary to `SWAPLAYER`. Environment configuration uses complete paths such as `SWAPLAYER_BILLING_STRIPE_SECRET_KEY`.

## Local agent tools

```bash
swaplayer-mcp
```

The stdio server exposes 13 documentation, configuration, and test tools. Test email/SMS and storage probes use the caller's local credentials and can cause provider charges or file changes. Clients must obtain approval before those calls. There is no hosted maintainer agent service, shared provider account, or maintainer token in the package. The dependency-free public contract server is `python mcp/server.py` from a source checkout.

## Compatibility and migration

The 1.x compatibility promise covers documented configuration, factory names, adapter method names, and normalized result fields. Underscore-prefixed helpers, vendor SDK objects, and historical development notes are outside that promise. Vendor behavior and access policies remain governed by the provider.

From 0.x: replace root `email`/`sms` settings with `communications`; use `send_email`, `send_sms`, and the storage adapter's `upload_file`/`get_file_url`/`file_exists` methods. Django storage `list_files` now returns a list of object dictionaries; `list_directory` preserves the former directory shape. WorkOS common list methods return object lists; `*_page` methods expose cursor envelopes. Stripe-specific payment/checkout options are keyword arguments after the common positional idempotency key. PayPal now handles zero-decimal HUF/JPY/TWD without dividing by 100; review provider-specific amount conventions when migrating. Tenant scopes must contain `{organization_id}` and reject unsafe paths; omitted contexts no longer grant system access.

## Documentation and contribution

- [Documentation index](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/README.md), [billing](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/billing.md), [storage](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/storage.md)
- [Email](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/email.md), [SMS](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/sms.md), [identity](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/identity-platform.md), [verification](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/identity-verification.md)
- [MCP tools](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/mcp.md), [security](https://github.com/Tunet-xyz/swap_layer/blob/main/SECURITY.md), [changelog](https://github.com/Tunet-xyz/swap_layer/blob/main/CHANGELOG.md)
- [Contributing](https://github.com/Tunet-xyz/swap_layer/blob/main/CONTRIBUTING.md), [shared versioning policy](https://github.com/Tunet-xyz/swap_layer/blob/main/VERSIONING.md), [release procedure](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/RELEASE.md)

Tests use mocked provider calls, plus installed-package and Django admin checks. They do not establish live provider certification or an independent security audit. Public PRs are welcome and require owner approval; repository jobs are manual and owner-gated.

MIT, copyright 2024–2026 Tunet Ltd. The [license](https://github.com/Tunet-xyz/swap_layer/blob/main/LICENSE) is included in source and wheel distributions.
