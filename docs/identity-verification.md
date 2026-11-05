# Stripe Identity in SwapLayer 1.0

Stripe Identity is the implemented verification provider. Persona and WorkOS verification adapters are not included. Install `SwapLayer[stripe]`; explicit configuration works without Django.

```python
import os
from swap_layer import configure, get_provider
configure(verification={"provider": "stripe", "stripe_secret_key": os.environ["STRIPE_IDENTITY_SECRET_KEY"]})
verification = get_provider("verification")
```

Create a session with `verification.create_verification_session(user, 'document', options={...})`. `user` is an application object with `id` (and optionally `username`); `options` may contain `return_url`, `email`, and `metadata`. The method returns a normalized session dictionary. Other operations retrieve/list/cancel/redact sessions and inspect verification status/reports. Listing returns the provider's dictionary envelope with `data` objects.

Webhook verification requires an endpoint signing secret passed to the provider constructor or configured as Django's `STRIPE_IDENTITY_WEBHOOK_SECRET`. Verify signatures against raw request bytes, then authorize and apply state changes in your application. Never trust a client redirect as proof of completed verification.

Use Stripe test mode and follow Stripe's current retention and production requirements. The library does not certify a person, decide compliance obligations, or implement an application's identity access policy. Redaction is a provider operation and needs explicit application authorization.

Optional Django model/admin mixins are under `swap_layer.identity.verification.models` and `.admin`. Applications own concrete models, migrations, access restrictions and retention. Runtime MCP tools provide guidance, not live production verification calls.
