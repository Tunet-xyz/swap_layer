# Identity Verification Infrastructure

This module handles identity verification for users. It follows the SwapLayer pattern, allowing for easy swapping of verification providers (e.g., Stripe, Onfido, etc.).

## Architecture

Following the standard SwapLayer pattern:

- **Adapter** (`adapter.py`): Abstract base class defining the provider interface.
- **Factory** (`factory.py`): Returns the configured provider instance.
- **Providers** (`providers/`): Contains provider implementations.
    - `stripe.py`: Stripe Identity implementation.
- **Models** (`models.py`): `IdentityVerificationSession` stores the state of verifications.
- **Schemas** (`schemas.py`): Pydantic models defining data contracts.
- **Operations** (`operations/core.py`): Business logic layer handling database operations and webhooks.

## Usage

### Direct Provider Usage (for simple operations)

```python
from swap_layer.identity.verification.factory import get_identity_verification_provider

provider = get_identity_verification_provider()
session_data = provider.create_verification_session(
    user=user,
    verification_type='document',
    options={'return_url': 'https://example.com/callback'}
)
```

### Using Operations Layer (for business logic)

The operations layer handles database persistence and webhook processing:

```python
from swap_layer.identity.verification.operations.core import IdentityOperations
from swap_layer.identity.verification.schemas import VerificationSessionCreate

ops = IdentityOperations()
session = ops.create_session(user, VerificationSessionCreate(...))
```

## Configuration

```python
# settings.py
IDENTITY_VERIFICATION_PROVIDER = 'stripe'  # or 'onfido' (when implemented)
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_IDENTITY_WEBHOOK_SECRET = os.environ.get('STRIPE_IDENTITY_WEBHOOK_SECRET')
```
