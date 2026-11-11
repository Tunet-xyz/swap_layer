"""swaplayer_migrate_billing_provider and its deprecated migrate_payment_provider alias."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from swap_layer.billing.management.commands import migrate_payment_provider as old_name
from swap_layer.billing.management.commands import swaplayer_migrate_billing_provider as new_name


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
