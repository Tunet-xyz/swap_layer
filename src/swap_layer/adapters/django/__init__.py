"""
Django integration helpers for SwapLayer.
"""

from swap_layer.settings import SwapLayerSettings, set_swaplayer_settings


def configure_from_django() -> SwapLayerSettings:
    """
    Load SwapLayer settings from Django and cache them for framework-neutral APIs.
    """
    settings = SwapLayerSettings.from_django()
    set_swaplayer_settings(settings)
    return settings


__all__ = ["configure_from_django"]
