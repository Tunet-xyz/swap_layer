# SwapLayer

[![PyPI](https://img.shields.io/pypi/v/SwapLayer)](https://pypi.org/project/SwapLayer/)
[![Python 3.10–3.13](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)](https://pypi.org/project/SwapLayer/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](https://github.com/Tunet-xyz/swap_layer/blob/main/LICENSE)

**One Python interface for billing, email, SMS, storage, identity, and
verification providers, with Django and FastAPI integrations.**

Part of the [Tunet](https://www.tunet.xyz/engineering/) open-source libraries, alongside [AccessGate](https://github.com/Tunet-xyz/access_gate), [GeoCanon](https://github.com/Tunet-xyz/geo_canon), and [SessionArmor](https://github.com/Tunet-xyz/session_armor). See the [SwapLayer product page](https://www.tunet.xyz/engineering/swap-layer/) for the public capability overview.

SwapLayer provides Python interfaces for billing, email, SMS, storage, and
identity integrations. Configure the services you use, then call their adapters
through `get_provider()`. Django supplies email, OAuth, model, and admin
integrations; a small FastAPI adapter attaches configuration to application
state.

## Features

| Service | Selectable provider values | Notes |
| --- | --- | --- |
| `email` | `django`, `smtp` | SendGrid, Mailgun, SES, and similar services use Django's Anymail backend settings. |
| `payments` | `stripe`, `paypal`, `square` | Capabilities differ; see the billing guide. |
| `sms` | `twilio`, `sns` | SNS history, delivery lookup, and balance are limited placeholders. |
| `storage` | `local`, `django`, `gcs` | S3/Azure use `django` with a configured Django storage backend. |
| `identity` | `workos`, `auth0` | Django OAuth integration; use the documented app registry. |
| `verification` | `stripe` | Stripe Identity; other verification providers are not implemented. |

Structured settings use `billing`, `communications.email`, `communications.sms`,
`storage`, `identity`, and `verification`. In plain Python call
`configure(...)`. In Django assign a `SwapLayerSettings` instance or dictionary
to `SWAPLAYER`. Environment configuration uses complete paths such as
`SWAPLAYER_BILLING_STRIPE_SECRET_KEY`; identity and verification settings cannot
be set from the environment.

## Version 1.0

The 1.x compatibility promise covers documented configuration, factory names,
adapter method names, and normalized result fields. Underscore-prefixed
helpers, vendor SDK objects, and historical development notes are outside that
promise. Vendor behavior and access policies remain governed by the provider.
Python 3.10–3.13 is tested, and the Django integrations support Django 4.2–6.x
(`Django<7`).

SwapLayer 1.0.0 is tagged (`v1.0.0`) but not yet published to PyPI, which still
serves 0.3.0. Until it is published, install 1.0.0 from the tag, adding extras
as needed:

```bash
pip install "SwapLayer @ git+https://github.com/Tunet-xyz/swap_layer@v1.0.0"
pip install "SwapLayer[stripe] @ git+https://github.com/Tunet-xyz/swap_layer@v1.0.0"
```

Upgrading from 0.x: replace root `email`/`sms` settings with `communications`;
use `send_email`, `send_sms`, and the storage adapter's
`upload_file`/`get_file_url`/`file_exists` methods. Django storage `list_files`
now returns a list of object dictionaries; `list_directory` preserves the former
directory shape. WorkOS common list methods return object lists; `*_page`
methods expose cursor envelopes. Stripe-specific payment/checkout options are
keyword arguments after the common positional idempotency key. PayPal now
handles zero-decimal HUF/JPY/TWD without dividing by 100; review
provider-specific amount conventions when migrating. Tenant scopes must contain
`{organization_id}` and reject unsafe paths; omitted contexts no longer grant
system access. See the [changelog](https://github.com/Tunet-xyz/swap_layer/blob/main/CHANGELOG.md).

## Installation

Core dependencies are Pydantic 2, Requests, and Tenacity.

```bash
pip install SwapLayer
pip install "SwapLayer[stripe]"     # Stripe 16.x
pip install "SwapLayer[email]"      # Django and django-anymail
pip install "SwapLayer[sms]"        # Twilio 9.x; add [aws] for SNS
pip install "SwapLayer[gcs]"        # Native Google Cloud Storage
pip install "SwapLayer[identity]"   # Django, WorkOS 10.x, Authlib
pip install "SwapLayer[mcp]"        # Local MCP SDK 1.x
```

Other extras: `django`, `fastapi`, `paypal`, `square`, `aws`, `azure`, `all`,
and `dev`. PayPal and Square use the core HTTP dependencies. Email and OAuth
require configured Django settings; storage, billing, Stripe Identity, and
Twilio support explicit configuration without Django.

## Quick start

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

Local URLs are plain paths; the library does not serve files or enforce URL
expiry. Applications must control access to private files. Keep the local
storage directory writable only by trusted application processes.

## Tenant-scoped storage

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

This produces `tenants/org-123/hello.txt`. Contexts consume identity already
verified by your application; they do not verify JWTs. Unscoped access needs an
explicit system context, such as `StorageSecurityContext.system_context()`.

## Billing

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

Pass integer provider minor currency units, represented by `Decimal` where
required by the adapter, to payment amounts. Provider IDs, tax rules, recurring
billing, and capability differences require application review. Stripe exposes
the broadest catalog, usage-meter, Entitlements, and webhook administration
surface.

## MCP server

SwapLayer includes a local stdio MCP server, installed with the `mcp` extra:

```bash
swaplayer-mcp
```

It exposes 13 documentation, configuration, and test tools. Test email/SMS
sends and storage probes use the caller's local credentials and can cause
provider charges or file changes, so clients must obtain approval before those
calls. There is no hosted maintainer agent service, shared provider account, or
maintainer token in the package. From a source checkout, `python mcp/server.py`
runs the dependency-free public contract server, which makes no network
connections. See [docs/mcp.md](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/mcp.md) and
[mcp/README.md](https://github.com/Tunet-xyz/swap_layer/blob/main/mcp/README.md) for the tools, methods, and limits.

## Scope and limitations

Provider capabilities differ. Moving a provider can require data migration,
webhook changes, and application changes. Unsupported operations raise errors
or have documented limitations.

Tests use mocked provider calls, plus installed-package and Django admin
checks. They do not establish live provider certification, and SwapLayer has
not had an independent security audit; the
[security assurance case](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/SECURITY_ASSURANCE.md) lists the evidence the
repository provides.

## Documentation

- [Documentation index](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/README.md): guides, security
  documents, and the release procedure.
- Guides: [billing](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/billing.md), [email](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/email.md), [SMS](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/sms.md), [storage](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/storage.md), [identity](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/identity-platform.md), [verification](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/identity-verification.md), [architecture](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/architecture.md), [MCP tools](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/mcp.md).
- Security: [security policy](https://github.com/Tunet-xyz/swap_layer/blob/main/SECURITY.md),
  [threat model](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/THREAT_MODEL.md),
  [security assurance](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/SECURITY_ASSURANCE.md),
  [audit scope](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/AUDIT_SCOPE.md), and
  [secure development](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/SECURE_DEVELOPMENT.md).
- [Changelog](https://github.com/Tunet-xyz/swap_layer/blob/main/CHANGELOG.md), including which versions reached PyPI.

## Development

```bash
git clone https://github.com/Tunet-xyz/swap_layer.git
cd swap_layer
python -m pip install -e ".[all,dev]"
python -m ruff check src tests
python -m mypy src/swap_layer
python -m bandit -r src
python -m pytest --cov=swap_layer --cov-branch
```

These are the checks the manual CI workflows run. The
[security assurance case](https://github.com/Tunet-xyz/swap_layer/blob/main/docs/SECURITY_ASSURANCE.md) lists the full
evidence commands, including the dependency audit.

## Contributing and releases

See [CONTRIBUTING.md](https://github.com/Tunet-xyz/swap_layer/blob/main/CONTRIBUTING.md) for the owner-reviewed contribution
process and [VERSIONING.md](https://github.com/Tunet-xyz/swap_layer/blob/main/VERSIONING.md) for the shared SemVer and
release policy. Report vulnerabilities privately as described in
[SECURITY.md](https://github.com/Tunet-xyz/swap_layer/blob/main/SECURITY.md). CI workflows run only when the maintainer
starts them, so include your local test results in pull requests. Everyone
taking part follows the [code of conduct](https://github.com/Tunet-xyz/swap_layer/blob/main/CODE_OF_CONDUCT.md).

## License

MIT. Copyright (c) 2024-2026 Tunet Ltd. See [LICENSE](https://github.com/Tunet-xyz/swap_layer/blob/main/LICENSE).
