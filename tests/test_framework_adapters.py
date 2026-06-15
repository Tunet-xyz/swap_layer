from types import SimpleNamespace

from swap_layer import configure
from swap_layer.adapters.django import configure_from_django
from swap_layer.adapters.fastapi import configure_fastapi
from swap_layer.settings import (
    SwapLayerSettings,
    get_swaplayer_settings,
    reset_swaplayer_settings,
)


def teardown_function():
    reset_swaplayer_settings()


def test_configure_sets_framework_neutral_settings():
    configured = configure({"storage": {"provider": "local", "media_root": "/tmp/media"}})

    assert isinstance(configured, SwapLayerSettings)
    assert get_swaplayer_settings().storage.media_root == "/tmp/media"


def test_django_adapter_loads_existing_django_settings():
    configured = configure_from_django()

    assert configured.communications.email.provider == "django"
    assert get_swaplayer_settings() is configured


def test_fastapi_adapter_attaches_settings_to_app_state():
    app = SimpleNamespace(state=SimpleNamespace())

    configured = configure_fastapi(app, {"storage": {"provider": "local", "media_url": "/assets/"}})

    assert app.state.swaplayer_settings is configured
    assert get_swaplayer_settings().storage.media_url == "/assets/"
