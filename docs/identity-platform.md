# Identity integration

Install `SwapLayer[identity]`. WorkOS 10.x and Authlib integrate with Django requests and sessions; this OAuth adapter is not a standalone JWT verifier. Authenticate and authorize requests in the application before privileged provider operations.

The current OAuth clients read Django app registries. The structured `identity` block selects the OAuth provider and validates configuration; retain the corresponding `WORKOS_APPS` or `AUTH0_APPS` registry for those clients.

```python
# Django settings.py
import os
WORKOS_APPS = {"default": {
    "api_key": os.environ["WORKOS_API_KEY"],
    "client_id": os.environ["WORKOS_CLIENT_ID"],
    "cookie_password": os.environ["WORKOS_COOKIE_PASSWORD"], # at least 32 characters
}}
SWAPLAYER = {"identity": {"provider": "workos", "workos_apps": WORKOS_APPS}}
```

Auth0 uses `AUTH0_APPS={'developer': {'client_id': ..., 'client_secret': ...}}`, `AUTH0_DEVELOPER_DOMAIN`, and `identity={'provider':'auth0','auth0_apps':AUTH0_APPS,'auth0_domain':AUTH0_DEVELOPER_DOMAIN}`. The factory maps the default Auth0 app to `developer`.

```python
from swap_layer import get_identity_client
identity = get_identity_client(app_name="default")
# In a Django view, with framework-managed session/state validation:
# url = identity.get_authorization_url(request, redirect_uri, state)
# user_data = identity.exchange_code_for_user(request, code)
# identity.clear_session(request)
```

Validate OAuth state, callback URLs, session ownership and logout destinations at the application boundary. Follow your provider's production session guidance. Normalized user data does not grant application permissions by itself.

## Management APIs

```python
from swap_layer.identity.platform.management.factory import get_management_client
management = get_management_client()
users = management.users.list_users(per_page=20)
```

`get_management_client()` currently follows Django's `IDENTITY_PROVIDER` setting (default `"workos"`) rather than `identity.provider`. WorkOS management reads its API key from `identity.workos_apps`; Auth0 management reads `AUTH0_APPS` and `AUTH0_DEVELOPER_DOMAIN`, with the same `default`-to-`developer` app mapping.

Common list methods return lists of object dictionaries. WorkOS `list_users_page`, `list_organizations_page`, `list_organization_members_page`, `list_logs_page`, and `list_roles_page` expose vendor response envelopes where applicable. WorkOS uses cursor arguments (`after`/`before`); numeric pages beyond zero are explicitly unsupported. Auth0 uses page/per-page arguments.

WorkOS role creation/removal and effective-permission lookup have unsupported operations that raise `NotImplementedError`. User-specific WorkOS event queries are rejected rather than returning every user's events. Auth0 `get_stats()` returns an active-user count; daily statistics return a list. Provider APIs have different capabilities and response semantics; test migrations with a non-production tenant.

Management access uses privileged caller credentials. Keep it in owner-authorized application flows and use least privilege. It is not exposed as a production operation by the MCP server. Applications own concrete Django identity models, migrations, permission checks, PII policies and audit retention.
