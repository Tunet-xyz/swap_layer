"""Validate array-shaped management API responses at the provider boundary."""

from typing import Any


def object_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError("Expected a JSON array of objects from the identity provider")
    return value
