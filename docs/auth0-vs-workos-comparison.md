# Auth0 and WorkOS

Both providers integrate with Django OAuth requests/sessions. Configure the app registries described in [identity-platform.md](identity-platform.md); migrating a provider requires session, user-ID and organization mapping review.

| Surface | Auth0 | WorkOS |
| --- | --- | --- |
| OAuth client | Authlib with Auth0 app/domain settings | WorkOS 10.x SDK with app/cookie settings |
| Common list methods | Object lists using page/per-page | Object lists using cursor arguments; page zero only |
| Raw cursor envelope helpers | Provider-specific responses | Explicit `*_page` methods |
| Role administration | Management API adapter | Several operations explicitly unsupported; role changes use organization membership |
| User-specific audit queries | Auth0 log query surface | Rejected where the adapter cannot enforce a user filter |
| Statistics | Active-user count and daily records | Provider-specific event/account facilities |

The interface normalizes a subset of operations. It does not imply provider feature parity or recommend an account plan. Review the selected provider's current documentation and test in a non-production tenant. Management keys belong to the caller and should have narrowly scoped privileges.
