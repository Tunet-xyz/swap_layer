"""Configuration output that never includes credential values."""

from typing import Any

from pydantic import BaseModel

# Settings fields whose values are options or public identifiers. Every other
# scalar field counts as sensitive, so credential fields added later stay
# hidden without a change here.
PUBLIC_CONFIG_FIELDS = frozenset(
    {
        "api_version",
        "auth0_domain",
        "bucket_name",
        "client_id",
        "debug",
        "from_number",
        "location",
        "location_id",
        "media_root",
        "media_url",
        "project_id",
        "provider",
        "publishable_key",
        "raise_on_error",
        "region_name",
        "sandbox",
        "sender_id",
        "storage_class",
        "webhook_id",
        "webhook_notification_url",
    }
)

_OMIT = object()


def redact_config(value: Any, mask: str | None = None) -> Any:
    """
    Return settings as plain data that shows only public field values.

    Pydantic models, mappings and sequences are walked recursively. A scalar
    is shown only when the field (or mapping key) that holds it is listed in
    ``PUBLIC_CONFIG_FIELDS``; any other scalar is omitted, or shown as ``mask``
    when a mask is given. Unset (``None``) values are kept.
    """
    result = _redact(value, mask, None)
    return None if result is _OMIT else result


def _redact(value: Any, mask: str | None, name: str | None) -> Any:
    if isinstance(value, BaseModel):
        value = {field: getattr(value, field) for field in type(value).model_fields}
    if isinstance(value, dict):
        redacted = ((str(key), _redact(item, mask, str(key))) for key, item in value.items())
        return {key: item for key, item in redacted if item is not _OMIT}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = (_redact(item, mask, name) for item in value)
        return [item for item in items if item is not _OMIT]
    if value is None or (name is not None and name.lower() in PUBLIC_CONFIG_FIELDS):
        return value
    return mask if mask is not None else _OMIT
