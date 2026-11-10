# Identity integration

Install `SwapLayer[identity]`. WorkOS 10.x and Authlib integrate with Django requests and sessions; this OAuth adapter is not a standalone JWT verifier. Authenticate and authorize requests in the application before privileged provider operations.

The OAuth clients read the structured `identity` settings (`workos_apps`, `auth0_apps`, `auth0_domain`) and fall back to the legacy `WORKOS_APPS`, `AUTH0_APPS` and `AUTH0_DEVELOPER_DOMAIN` Django settings.

```python
# Django settings.py
import os
SWAPLAYER = {"identity": {"provider": "workos", "workos_apps": {"default": {
    "api_key": os.environ["WORKOS_API_KEY"],
    "client_id": os.environ["WORKOS_CLIENT_ID"],
    "cookie_password": os.environ["WORKOS_COOKIE_PASSWORD"],  # a Fernet key
}}}}
```

`cookie_password` must be a Fernet key (32 url-safe base64-encoded bytes), which WorkOS SDK 10 uses to seal sessions; a password of another form is rejected. Generate one with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Auth0 uses `identity={'provider': 'auth0', 'auth0_apps': {'developer': {'client_id': ..., 'client_secret': ...}}, 'auth0_domain': ...}`, or the legacy `AUTH0_APPS` and `AUTH0_DEVELOPER_DOMAIN` settings. The factory maps the default Auth0 app to `developer`. An app may also set `management_client_id` and `management_client_secret` for the Management API.

```python
from swap_layer import get_identity_client
identity = get_identity_client(app_name="default")
# Sign-in view: the client keeps the OAuth state in request.session.
# url = identity.get_authorization_url(request, redirect_uri)
# Callback view: the request's state must match one issued to this session.
# user_data = identity.exchange_code_for_user(request, code)
# identity.clear_session(request)
```

WorkOS accepts each state once, within 10 minutes of `get_authorization_url`; otherwise `exchange_code_for_user` raises `OAuthStateError` (from `swap_layer.identity.platform.adapter`). The Auth0 client keeps its state and nonce in the session for Authlib to check. Validate callback URLs, session ownership and logout destinations at the application boundary. Follow your provider's production session guidance. Normalized user data does not grant application permissions by itself.

## Management APIs

```python
from swap_layer.identity.platform.management.factory import get_management_client
management = get_management_client()
users = management.users.list_users(per_page=20)
```

`get_management_client()` uses `identity.provider`, or the legacy `IDENTITY_PROVIDER` Django setting (default `"workos"`) when SwapLayer settings have no `identity`. WorkOS management reads its API key from `identity.workos_apps` (or the legacy `WORKOS_APPS`). Auth0 management reads `identity.auth0_apps` and `identity.auth0_domain` (or the legacy `AUTH0_APPS` and `AUTH0_DEVELOPER_DOMAIN`), with the same `default`-to-`developer` app mapping, and uses an app's `management_client_id` and `management_client_secret` when they are set, otherwise its OAuth client credentials.

Common list methods return lists of object dictionaries. WorkOS `list_users_page`, `list_organizations_page`, `list_organization_members_page`, `list_logs_page`, and `list_roles_page` expose vendor response envelopes where applicable. WorkOS uses cursor arguments (`after`/`before`); numeric pages beyond zero are explicitly unsupported. Auth0 uses page/per-page arguments.

WorkOS role creation/removal and effective-permission lookup have unsupported operations that raise `NotImplementedError`. User-specific WorkOS event queries are rejected rather than returning every user's events. Auth0 `get_stats()` returns an active-user count; daily statistics return a list. Provider APIs have different capabilities and response semantics; test migrations with a non-production tenant.

Management access uses privileged caller credentials. Keep it in owner-authorized application flows and use least privilege. It is not exposed as a production operation by the MCP server. Applications own concrete Django identity models, migrations, permission checks, PII policies and audit retention.
