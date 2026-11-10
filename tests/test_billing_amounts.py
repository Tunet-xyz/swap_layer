"""Stripe and Square accept integer minor units and never truncate fractions."""

from decimal import Decimal
from unittest.mock import MagicMock, Mock

import pytest

from swap_layer.billing.adapter import PaymentValidationError, minor_units

pytest.importorskip("stripe")

from swap_layer.billing.providers.square import SquarePaymentProvider  # noqa: E402
from swap_layer.billing.providers.stripe import StripePaymentProvider  # noqa: E402

FRACTIONS = [Decimal("12.5"), Decimal("1234.01"), 12.5, "12.34", "0.5"]
INVALID = [*FRACTIONS, True, Decimal("NaN"), Decimal("Infinity"), "abc", ""]


@pytest.mark.parametrize(
    ("amount", "expected"),
    [(Decimal("1234"), 1234), (1234, 1234), ("1234", 1234), (Decimal("1234.00"), 1234), (12.0, 12), (0, 0)],
)
def test_integral_minor_units_are_accepted(amount, expected):
    assert minor_units(amount) == expected


@pytest.mark.parametrize("amount", INVALID)
def test_fractions_and_non_numbers_are_rejected(amount):
    with pytest.raises(PaymentValidationError, match="minor units"):
        minor_units(amount)


def stripe_provider():
    provider = StripePaymentProvider(secret_key="sk_test_123")
    provider._client = MagicMock()
    return provider


@pytest.mark.parametrize("amount", FRACTIONS)
def test_stripe_rejects_fractional_amounts_before_calling_stripe(amount):
    provider = stripe_provider()
    with pytest.raises(PaymentValidationError):
        provider.create_payment_intent(amount=amount, currency="usd")
    with pytest.raises(PaymentValidationError):
        provider.create_price(product_id="prod_1", amount=amount, currency="usd")
    with pytest.raises(PaymentValidationError):
        provider.create_refund(payment_intent_id="pi_1", amount=amount)
    assert provider._client.mock_calls == []


def test_stripe_sends_integer_minor_units():
    provider = stripe_provider()
    provider.create_payment_intent(amount=Decimal("1234"), currency="usd")
    params = provider._client.v1.payment_intents.create.call_args.kwargs["params"]
    assert params["amount"] == 1234
    assert isinstance(params["amount"], int)


def test_square_money_uses_integer_minor_units():
    assert SquarePaymentProvider._money(Decimal("1234"), "usd") == {"amount": 1234, "currency": "USD"}
    assert SquarePaymentProvider._money("1234", "gbp") == {"amount": 1234, "currency": "GBP"}
    for amount in FRACTIONS:
        with pytest.raises(PaymentValidationError):
            SquarePaymentProvider._money(amount, "usd")


def test_square_refund_rejects_fractions_without_a_request():
    provider = SquarePaymentProvider(access_token="token", location_id="LOC")
    provider.session.request = Mock()
    with pytest.raises(PaymentValidationError):
        provider.create_refund(payment_intent_id="PAY-1", amount=Decimal("10.5"))
    provider.session.request.assert_not_called()


@pytest.mark.parametrize(
    "amount", ["1e800000", Decimal("1E+800000"), "1" * 70, Decimal("1E+19"), "1." + "0" * 200]
)
def test_huge_amounts_are_rejected_quickly(amount):
    import time

    started = time.perf_counter()
    with pytest.raises(PaymentValidationError):
        minor_units(amount)
    assert time.perf_counter() - started < 0.5


def test_largest_accepted_amount():
    assert minor_units("999999999999999999") == 999999999999999999
