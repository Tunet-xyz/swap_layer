"""Settings paths shown in errors, hints and docstrings exist in the settings schema."""

import ast
import re

import pytest
from pydantic import BaseModel

from swap_layer.exceptions import (
    ModuleNotConfiguredError,
    MultiTenantConfigError,
    ProviderConfigMismatchError,
    StripeKeyError,
    TwilioConfigError,
    WorkOSConfigError,
)
from swap_layer.settings import SwapLayerSettings, _env_path, _nested_model


def assert_path(path: str) -> None:
    """Walk SWAPLAYER.a.b.c through the schema; '<...>' parts stand for mapping keys."""
    parts = path.removeprefix("SWAPLAYER.").split(".")
    model: type[BaseModel] | None = SwapLayerSettings
    expect_key = False
    for part in parts:
        assert model is not None, f"{path}: {part} is below a scalar field"
        if expect_key:
            expect_key = False
            continue
        assert part in model.model_fields, f"{path}: no field {part!r} in {model.__name__}"
        kind, nested = _nested_model(model.model_fields[part].annotation)
        model = nested
        expect_key = kind == "mapping"


def assert_example(example: str) -> None:
    """An example 'key={...}' uses only schema fields."""
    key, _, value = example.partition("=")

    def walk(model: type[BaseModel], data: dict) -> None:
        for name, item in data.items():
            assert name in model.model_fields, f"{example}: no field {name!r} in {model.__name__}"
            kind, nested = _nested_model(model.model_fields[name].annotation)
            if kind == "model" and isinstance(item, dict):
                walk(nested, item)
            elif kind == "mapping" and isinstance(item, dict):
                for app in item.values():
                    walk(nested, app)

    walk(SwapLayerSettings, {key.strip(): ast.literal_eval(value.replace("{...}", "{}"))})


MISMATCHES = [
    ("billing", "stripe", "stripe"),
    ("billing", "paypal", "paypal"),
    ("billing", "square", "square"),
    ("communications.sms", "twilio", "twilio"),
    ("communications.sms", "sns", "sns"),
    ("sms", "twilio", "twilio"),  # former module name still maps to the real path
    ("identity", "workos", "workos_apps"),
    ("identity", "auth0", "auth0_apps"),
    ("identity", "auth0", "auth0_domain"),
    ("verification", "stripe", "stripe_secret_key"),
]


@pytest.mark.parametrize(("module", "provider", "missing"), MISMATCHES)
def test_provider_mismatch_errors_name_real_settings(module, provider, missing):
    error = ProviderConfigMismatchError(module, provider, missing)
    for path in error.related_settings:
        assert_path(path)
    assert error.related_settings[-1].endswith(f".{missing}")
    for example in error.examples:
        assert_example(example)


def test_settings_validation_raises_errors_with_real_paths():
    with pytest.raises(ProviderConfigMismatchError) as exc_info:
        SwapLayerSettings(communications={"sms": {"provider": "twilio"}})
    assert "SWAPLAYER.communications.sms.twilio" in exc_info.value.related_settings
    assert "SMS provider 'twilio'" in str(exc_info.value)


@pytest.mark.parametrize(
    "error",
    [
        StripeKeyError("secret key", "pk_test"),
        TwilioConfigError.invalid_account_sid("XX"),
        TwilioConfigError.invalid_phone_number("555"),
        WorkOSConfigError.invalid_cookie_password(8),
        MultiTenantConfigError("app", "workos", []),
        *[ModuleNotConfiguredError(m) for m in ("billing", "communications", "storage", "identity", "verification")],
    ],
)
def test_other_configuration_errors_name_real_settings(error):
    for path in error.related_settings:
        assert_path(path.replace("<app_name>", "app"))


def test_from_env_docstring_names_resolve():
    doc = SwapLayerSettings.from_env.__doc__ or ""
    names = re.findall(r"SWAPLAYER_([A-Z0-9_]+)=", doc)
    assert len(names) >= 8
    for name in names:
        assert _env_path(SwapLayerSettings, name.lower().split("_")) is not None, name
