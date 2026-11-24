"""PayPal and Square refuse unconfigured webhooks, bound their requests, and raise payment errors."""

from unittest.mock import Mock

import pytest

from swap_layer.billing.adapter import (
    PaymentConnectionError,
    PaymentError,
    PaymentValidationError,
    ResourceNotFoundError,
)
from swap_layer.billing.providers.paypal import PayPalPaymentProvider
from swap_layer.billing.providers.square import SquarePaymentProvider


class Response:
    def __init__(self, payload=None, status_code=200, text=None):
        self.payload = payload
        self.status_code = status_code
        self.content = b"" if payload is None else b"{}"
        self.text = text if text is not None else ("" if payload is None else str(payload))

    def json(self):
        if self.payload is None:
            raise ValueError("no JSON body")
        return self.payload


def paypal(**overrides):
    options = {"client_id": "paypal-client", "client_secret": "paypal-secret", "webhook_id": "WH-1"}
    options.update(overrides)
    provider = PayPalPaymentProvider(**options)
    provider.session.post = Mock(return_value=Response({"access_token": "token-1"}))
    return provider


def square(**overrides):
    options = {
        "access_token": "square-token",
        "location_id": "LOC-1",
        "webhook_signature_key": "signature-key",
        "webhook_notification_url": "https://app.example.com/square/webhook",
    }
    options.update(overrides)
    return SquarePaymentProvider(**options)


def test_paypal_webhook_verification_needs_a_webhook_id():
    provider = paypal(webhook_id=None)
    provider.session.request = Mock()

    with pytest.raises(ValueError, match="webhook_id is required"):
        provider.verify_webhook_signature(b"{}", "signature", headers={})
    provider.session.request.assert_not_called()


@pytest.mark.parametrize("missing", ["webhook_signature_key", "webhook_notification_url"])
def test_square_webhook_verification_needs_its_key_and_url(missing):
    provider = square(**{missing: None})

    with pytest.raises(ValueError, match="webhook_signature_key and webhook_notification_url are required"):
        provider.verify_webhook_signature(b'{"event_id": "evt-1"}', "c2lnbmF0dXJl")


def test_paypal_requests_have_a_30_second_timeout():
    provider = paypal()
    provider.session.request = Mock(return_value=Response({"id": "INV-1"}))

    provider._request("GET", "/v2/invoicing/invoices/INV-1")

    assert provider.session.post.call_args.kwargs["timeout"] == 30
    assert provider.session.request.call_args.kwargs["timeout"] == 30


def test_square_requests_have_a_30_second_timeout():
    provider = square()
    provider.session.request = Mock(return_value=Response({"location": {"id": "LOC-1"}}))

    provider._request("GET", "/v2/locations/LOC-1")

    assert provider.session.request.call_args.kwargs["timeout"] == 30


@pytest.mark.parametrize(
    ("response", "error", "message"),
    [
        (Response({"errors": [{"category": "API_ERROR"}]}, 500, text="upstream failed"), PaymentConnectionError, "upstream failed"),
        (Response({"errors": [{"code": "NOT_FOUND"}]}, 404), ResourceNotFoundError, "NOT_FOUND"),
        (Response({"errors": [{"detail": "Bad card", "code": "CARD_DECLINED"}]}, 400), PaymentValidationError, "Bad card"),
        (Response({"errors": "not a list"}, 400, text="bad request"), PaymentValidationError, "bad request"),
        (Response(["not", "an", "object"], 400, text="bad request"), PaymentValidationError, "bad request"),
        (Response(None, 404, text=""), ResourceNotFoundError, "Square returned HTTP 404"),
        (Response({}, 418, text=""), PaymentError, "Square returned HTTP 418"),
    ],
)
def test_square_error_responses_raise_payment_errors_with_text(response, error, message):
    with pytest.raises(error) as raised:
        square()._handle_response(response)

    assert message in str(raised.value)


@pytest.mark.parametrize(
    ("response", "error", "message"),
    [
        (Response({"message": {"nested": "detail"}}, 400), PaymentValidationError, "nested"),
        (Response({"name": "RESOURCE_NOT_FOUND"}, 404), ResourceNotFoundError, "RESOURCE_NOT_FOUND"),
        (Response(None, 502, text="Bad gateway"), PaymentConnectionError, "Bad gateway"),
        (Response(["not", "an", "object"], 500, text="server error"), PaymentConnectionError, "server error"),
        (Response({}, 418, text=""), PaymentError, "PayPal returned HTTP 418"),
    ],
)
def test_paypal_error_responses_raise_payment_errors_with_text(response, error, message):
    with pytest.raises(error) as raised:
        paypal()._handle_response(response)

    assert message in str(raised.value)
