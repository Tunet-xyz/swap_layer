# SwapLayer — Copilot Custom Instructions

## Project Overview

SwapLayer is a **unified infrastructure abstraction layer for Django SaaS** that eliminates vendor lock-in. It provides a consistent Python API across email, payments, SMS, storage, identity, and verification providers. Developers change a config setting to swap providers — zero code changes.

- **Language**: Python 3.10+
- **Framework**: Django 4.2+
- **Config**: Pydantic v2 (`SwapLayerSettings`)
- **Tests**: pytest
- **Linting**: ruff
- **Types**: mypy (non-blocking)

## Architecture — The Adapter Pattern

Every module follows the same structure. Understand this and you understand the whole codebase:

```
src/swap_layer/{module}/
├── __init__.py          # Public exports + get_provider alias
├── adapter.py           # Abstract base class (ABC) — the contract
├── factory.py           # Factory function — reads config, returns provider
├── models.py            # Django models (optional)
├── admin.py             # Django admin (optional)
├── apps.py              # Django app config
└── providers/
    ├── __init__.py
    └── {provider}.py    # Concrete implementation
```

**Key files to understand the pattern:**
- `src/swap_layer/billing/adapter.py` — abstract interface
- `src/swap_layer/billing/factory.py` — factory that reads settings
- `src/swap_layer/billing/providers/stripe.py` — concrete implementation

## Modules

| Module | Path | Adapters |
|--------|------|----------|
| Billing/Payments | `billing/` | `PaymentProviderAdapter`, `CustomerAdapter`, `SubscriptionAdapter`, `PaymentAdapter`, `ProductAdapter` |
| Email | `communications/email/` | `EmailProviderAdapter` |
| SMS | `communications/sms/` | `SMSProviderAdapter` |
| Storage | `storage/` | `StorageProviderAdapter` |
| Identity Platform | `identity/platform/` | `AuthProviderAdapter` |
| Identity Verification | `identity/verification/` | `IdentityVerificationProviderAdapter` |
| MCP Server | `mcp/` | AI assistant integration |

## Configuration System

All configuration lives in `src/swap_layer/settings.py` using Pydantic:

```python
# In Django settings.py
from swap_layer.settings import SwapLayerSettings

SWAPLAYER = SwapLayerSettings(
    billing={'provider': 'stripe', 'stripe': {'secret_key': 'sk_...'}},
    communications={
        'email': {'provider': 'django'},
        'sms': {'provider': 'twilio', 'twilio': {...}},
    },
    storage={'provider': 's3'},
)
```

- `SwapLayerSettings` — main config class
- `get_swaplayer_settings()` — cached instance from Django settings
- `validate_swaplayer_config()` — validation helper
- Each module has a Pydantic config class: `StripeConfig`, `TwilioConfig`, etc.
- Legacy Django settings still supported via `_from_legacy_django_settings()`

## Unified Entry Point

```python
from swap_layer import get_provider

email    = get_provider('email')
payments = get_provider('payments')  # alias: 'billing'
sms      = get_provider('sms')
storage  = get_provider('storage')
identity = get_provider('identity')  # aliases: 'auth', 'oauth'
kyc      = get_provider('verification')  # alias: 'kyc'
```

## Coding Conventions

### When adding a new provider

1. Create `providers/{name}.py` inheriting from the module's adapter ABC
2. Implement every `@abstractmethod`
3. Use lazy imports for optional third-party SDKs (import inside `__init__`)
4. Normalize all responses to plain dicts — never return raw SDK objects
5. Register the provider in the module's `factory.py`
6. Add the optional dependency to `pyproject.toml` under `[project.optional-dependencies]`

### When adding a new module

1. Follow the directory structure above exactly
2. Create the adapter ABC in `adapter.py`
3. Create the factory function in `factory.py`
4. Add config class to `src/swap_layer/settings.py`
5. Register in `src/swap_layer/__init__.py` `get_provider()`
6. Add tests in `tests/test_{module}.py`
7. Add documentation in `docs/{module}.md`

### Error handling

- All custom exceptions inherit from `SwapLayerError` (see `exceptions.py`)
- Use `ConfigurationError` for config issues, `ProviderError` for runtime failures
- Always mask secrets in error messages using `_mask_secret()`
- Include `hint`, `docs_url`, and `examples` in error constructors

### Testing patterns

- Tests live in `tests/test_{module}.py`
- Use `@pytest.mark.django_db` for database tests
- Mock external SDKs — never call real APIs in tests
- The `conftest.py` sets up Django settings with `SWAPLAYER` dict
- Factory tests verify that `get_swaplayer_settings()` is used

### Import conventions

- Lazy imports for optional dependencies:
  ```python
  def __init__(self):
      try:
          import stripe
      except ImportError:
          raise ImportError("Install with: pip install 'SwapLayer[stripe]'")
      self.client = stripe
  ```
- Direct imports for core dependencies (Django, Pydantic)

### Documentation standards

- Root: only `README.md`
- User docs: `docs/{topic}.md`
- Dev docs: `docs/development/`
- Module docs: max 3 files (`README.md` required, `GUIDE.md` and `DECISIONS.md` optional)
- No markdown files outside these locations

### Commit messages

```
type(scope): Brief description

Types: feat, fix, docs, style, refactor, test, chore
```

## Known Issues & Legacy Code

- `src/swap_layer/config.py` is a vestigial Django settings proxy — `settings.py` is the canonical config system
- Factory files have backward-compatibility fallbacks to legacy individual Django settings (e.g., `PAYMENT_PROVIDER`, `STRIPE_SECRET_KEY`)
- `billing/products/` is a placeholder — adapter defined but no implementations
- Some provider methods are stubs (e.g., SNS `list_messages()`, Twilio `opt_out_number()`)
- Identity management (WorkOS) has `NotImplementedError` for operations the WorkOS API doesn't support

## File Importance (Read These First)

1. `src/swap_layer/__init__.py` — public API and `get_provider()`
2. `src/swap_layer/settings.py` — configuration system
3. `src/swap_layer/exceptions.py` — error hierarchy
4. `src/swap_layer/billing/adapter.py` — canonical adapter pattern example
5. `src/swap_layer/billing/factory.py` — canonical factory pattern example
6. `docs/architecture.md` — design philosophy
7. `tests/conftest.py` — test setup
