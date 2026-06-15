"""
FastAPI integration helpers for SwapLayer.
"""

from typing import Any

from swap_layer.settings import SwapLayerSettings, set_swaplayer_settings


def configure_fastapi(
    app: Any,
    settings: SwapLayerSettings | dict[str, Any] | None = None,
    *,
    env_prefix: str = "SWAPLAYER_",
) -> SwapLayerSettings:
    """
    Attach SwapLayer settings to a FastAPI app and cache them for provider factories.

    FastAPI is intentionally not imported here, so the adapter remains lightweight
    and can be used by compatible ASGI app objects in tests.
    """
    if settings is None:
        resolved = SwapLayerSettings.from_env(prefix=env_prefix)
    elif isinstance(settings, SwapLayerSettings):
        resolved = settings
    else:
        resolved = SwapLayerSettings(**settings)

    set_swaplayer_settings(resolved)
    app.state.swaplayer_settings = resolved
    return resolved


__all__ = ["configure_fastapi"]
