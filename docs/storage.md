# Storage in SwapLayer 1.0

Select `local`, `gcs`, or `django`. Direct S3 and Azure adapter classes are not exposed; use Django's configured storage backend for those services.

```python
from io import BytesIO
from swap_layer import configure, get_provider

configure(storage={"provider": "local", "media_root": "./media"})
storage = get_provider("storage")
storage.upload_file("docs/example.txt", BytesIO(b"example"))
contents = storage.download_file("docs/example.txt")
objects = storage.list_files(prefix="docs/", max_results=100)
url = storage.get_file_url("docs/example.txt")
```

Common operations: `upload_file`, `download_file`, `delete_file`, `delete_files`, `file_exists`, `get_file_metadata`, `list_files`, `get_file_url`, `copy_file`, `move_file`, and `generate_presigned_upload_url`. Presigned uploads and expiry are backend-dependent. Local storage returns an upload placeholder and plain URLs; Django's generic adapter cannot generate presigned uploads. The application serves local URLs and enforces access control.

`list_files` returns a list of dictionaries with `file_path` and backend metadata. Django's former `{files, directories}` result is available through `list_directory`.

## Tenant boundaries

```python
from swap_layer.storage.security import StorageSecurityContext, storage_context

ctx = StorageSecurityContext(
    organization_id="org-123", user_id="user-456", role="member",
    scope_format="tenants/{organization_id}",
)
with storage_context(storage, ctx) as scoped:
    scoped.upload_from_string("report.txt", "example")
    assert scoped.download_as_text("report.txt") == "example"
```

A member may read/write; a viewer may read; managers and admins may delete. Unknown roles receive no permissions. Explicit permission sets override the role mapping. The context consumes trusted, previously verified identity; it does not verify JWTs or determine membership. Never populate it directly from unverified claims.

Non-system scopes must include `{organization_id}`. Identity fields are single safe segments; traversal, absolute paths, backslashes and drive/stream paths are rejected. Explicit system access is `StorageSecurityContext.system_context(reason="maintenance")`. Missing contexts fail closed.

Local storage rejects symlinks and junctions below its configured root, including metadata sidecars. The storage root and its parents must be writable only by trusted application processes: this is not an OS sandbox against concurrent filesystem replacement. `download_file(destination=...)` writes to a caller-specified local destination; validate that destination in your application. MD5 ETags are change indicators, not security checksums.

## Native GCS

Install `SwapLayer[gcs]`. Google application default credentials are supported; a credentials file is optional.

```python
configure(storage={
    "provider": "gcs", "bucket_name": "your-bucket", "project_id": "your-project",
})
```

`credentials_path`, `location`, and `storage_class` are optional settings. GCS URL signing requires credentials capable of signing. Extended bucket methods are provider-specific and are outside the common adapter surface.

## Django storage backends

Install `SwapLayer[aws]` for S3 or `SwapLayer[azure]` for Azure, configure Django's `STORAGES['default']` backend, then use `SWAPLAYER = {'storage': {'provider': 'django'}}`. Do not set the SwapLayer provider to `s3` or `azure`. Django 4.2–6.x is supported subject to each Python version's requirements. Backend ACLs, URL expiry, credentials, and serving policies remain application configuration.

Optional model/admin mixins live in `swap_layer.storage.models` and `swap_layer.storage.admin`; subclass the abstract models in your application and manage their migrations there.
