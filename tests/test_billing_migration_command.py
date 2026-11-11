"""swaplayer_migrate_billing_provider and its deprecated migrate_payment_provider alias."""

from io import StringIO
from unittest.mock import patch

import pytest
from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from swap_layer.billing.factory import get_payment_provider
from swap_layer.billing.management.commands import migrate_payment_provider as old_name
from swap_layer.billing.management.commands import swaplayer_migrate_billing_provider as new_name
from swap_layer.billing.providers.paypal import PayPalPaymentProvider
from swap_layer.billing.providers.square import SquarePaymentProvider
from swap_layer.settings import SwapLayerSettings

SQUARE = {"access_token": "square-token", "location_id": "LOC-1"}
PAYPAL = {"client_id": "paypal-client", "client_secret": "paypal-secret"}


def test_old_name_is_a_deprecated_alias_of_the_new_command():
    assert issubclass(old_name.Command, new_name.Command)
    assert old_name.Command.help.startswith("Deprecated alias of swaplayer_migrate_billing_provider.")
    err = StringIO()
    with pytest.warns(DeprecationWarning, match="use swaplayer_migrate_billing_provider"):
        with pytest.raises(CommandError, match="--dry-run or --confirm"):
            call_command(old_name.Command(), "stripe", "paypal", stderr=err)
    assert "use swaplayer_migrate_billing_provider" in err.getvalue()


def test_new_name_does_not_warn(recwarn):
    with pytest.raises(CommandError, match="--dry-run or --confirm"):
        call_command(new_name.Command(), "stripe", "paypal", stderr=StringIO())
    assert not [w for w in recwarn if issubclass(w.category, DeprecationWarning)]


def configured(**billing) -> SwapLayerSettings:
    return SwapLayerSettings(billing={"provider": "square", "square": SQUARE, **billing})


def test_a_named_provider_is_built_from_its_own_block():
    with patch("swap_layer.billing.factory.get_swaplayer_settings", return_value=configured(paypal=PAYPAL)):
        assert isinstance(get_payment_provider(), SquarePaymentProvider)
        target = get_payment_provider("paypal")
    assert isinstance(target, PayPalPaymentProvider)
    assert target.client_id == "paypal-client"


def test_a_named_provider_without_a_block_uses_its_legacy_settings():
    with patch("swap_layer.billing.factory.get_swaplayer_settings", return_value=configured()):
        with override_settings(PAYPAL_CLIENT_ID="legacy-client", PAYPAL_CLIENT_SECRET="legacy-secret"):
            target = get_payment_provider("paypal")
    assert target.client_id == "legacy-client"


def test_unknown_provider_names_are_rejected():
    with pytest.raises(ValueError, match="Unknown Payment Provider"):
        get_payment_provider("provider")


class Customers(list):
    def filter(self, **kwargs):
        assert kwargs == {"payment_provider": "square"}
        return self

    def exclude(self, **kwargs):
        return self

    def count(self):
        return len(self)


class Customer:
    def __init__(self, pk, email):
        self.pk, self.email = pk, email
        self.payment_provider, self.payment_customer_id = "square", f"SQ-{pk}"
        self.saved = None

    def save(self, update_fields):
        self.saved = update_fields


def migrate(*args: str) -> tuple[list[Customer], str]:
    customers = Customers([Customer(1, "a@example.com")])
    model = type("Model", (), {"payment_provider": None, "payment_customer_id": None, "objects": customers})
    out = StringIO()
    with (
        patch("swap_layer.billing.factory.get_swaplayer_settings", return_value=configured(paypal=PAYPAL)),
        patch.object(apps, "get_model", return_value=model),
        patch.object(SquarePaymentProvider, "create_customer") as square_create,
    ):
        call_command(new_name.Command(), "square", *args, "--model", "shop.Customer", stdout=out)
    square_create.assert_not_called()
    return customers, out.getvalue()


def test_confirmed_migration_creates_customers_in_the_target_provider():
    (customer,), output = migrate("paypal", "--confirm")
    assert customer.payment_provider == "paypal"
    assert customer.payment_customer_id == "paypal:a@example.com"  # PayPal's local handle
    assert customer.saved == ["payment_provider", "payment_customer_id"]
    assert "Migrated: 1" in output


def test_an_unknown_target_provider_is_a_command_error():
    with pytest.raises(CommandError, match='Cannot use billing provider "nope"'):
        migrate("nope", "--confirm")
