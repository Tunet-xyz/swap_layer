"""Invoice listing returns only the requested customer's invoices."""

from unittest.mock import Mock

import pytest

from swap_layer.billing.adapter import PaymentValidationError
from swap_layer.billing.providers.paypal import PayPalPaymentProvider
from swap_layer.billing.providers.square import SquarePaymentProvider


class DummyResponse:
    def __init__(self, payload=None, status_code=200):
        self.payload = payload or {}
        self.status_code = status_code
        self.content = b"{}" if payload is not None else b""
        self.text = str(self.payload)

    def json(self):
        return self.payload


def paypal_provider():
    provider = PayPalPaymentProvider(
        client_id="paypal-client",
        client_secret="paypal-secret",
        webhook_id="WH-123",
    )
    provider.session.post = Mock(return_value=DummyResponse({"access_token": "token-123"}))
    return provider


def paypal_invoice(invoice_id, *emails):
    return {
        "id": invoice_id,
        "status": "SENT",
        "detail": {"invoice_date": "2026-11-01"},
        "primary_recipients": [{"billing_info": {"email_address": email}} for email in emails],
        "amount": {"value": "10.00", "currency_code": "USD"},
    }


def square_provider():
    return SquarePaymentProvider(
        access_token="square-token",
        location_id="LOC-123",
        webhook_signature_key="signature-key",
        webhook_notification_url="https://app.example.com/square/webhook",
    )


def square_invoice(invoice_id, customer_id):
    recipient = {"customer_id": customer_id} if customer_id else {}
    return {
        "id": invoice_id,
        "status": "UNPAID",
        "created_at": "2026-11-01T10:00:00Z",
        "primary_recipient": recipient,
        "public_url": f"https://squareup.com/pay-invoice/{invoice_id}",
        "payment_requests": [
            {"computed_amount_money": {"amount": 1000, "currency": "USD"}}
        ],
        "invoice_total_money": {"amount": 1000, "currency": "USD"},
    }


def test_paypal_list_invoices_searches_by_the_customer_email():
    provider = paypal_provider()
    provider.session.request = Mock(
        return_value=DummyResponse(
            {
                "items": [
                    paypal_invoice("INV-1", "Alice@Example.com"),
                    paypal_invoice("INV-2", "bob@example.com"),
                    {"id": "INV-3", "status": "DRAFT"},
                ]
            }
        )
    )

    invoices = provider.list_invoices("paypal:alice@example.com", limit=5)

    assert [invoice["id"] for invoice in invoices] == ["INV-1"]
    assert invoices[0]["customer_id"] == "paypal:Alice@Example.com"
    method, url = provider.session.request.call_args.args
    assert method == "POST"
    assert url.endswith("/v2/invoicing/search-invoices?page=1&page_size=5")
    assert provider.session.request.call_args.kwargs["json"] == {
        "recipient_email": "alice@example.com"
    }


def test_paypal_list_invoices_matches_any_primary_recipient():
    provider = paypal_provider()
    provider.session.request = Mock(
        return_value=DummyResponse(
            {"items": [paypal_invoice("INV-1", "billing@example.com", "alice@example.com")]}
        )
    )

    invoices = provider.list_invoices("paypal:alice@example.com")

    assert [invoice["id"] for invoice in invoices] == ["INV-1"]
    assert invoices[0]["customer_id"] == "paypal:billing@example.com"


@pytest.mark.parametrize("customer_id", ["PAYER-123", "", "paypal:"])
def test_paypal_list_invoices_refuses_ids_it_cannot_scope(customer_id):
    provider = paypal_provider()
    provider.session.request = Mock()

    with pytest.raises(PaymentValidationError):
        provider.list_invoices(customer_id)

    provider.session.request.assert_not_called()


def test_paypal_invoice_without_recipient_has_no_customer():
    provider = paypal_provider()

    assert provider._normalize_invoice({"id": "INV-9"})["customer_id"] is None


def test_square_list_invoices_searches_one_customer_at_the_location():
    provider = square_provider()
    provider.session.request = Mock(
        return_value=DummyResponse(
            {
                "invoices": [
                    square_invoice("inv-1", "CUST-1"),
                    square_invoice("inv-2", None),
                    square_invoice("inv-3", "CUST-2"),
                ]
            }
        )
    )

    invoices = provider.list_invoices("CUST-1", limit=7)

    assert [invoice["id"] for invoice in invoices] == ["inv-1"]
    assert invoices[0]["hosted_invoice_url"] == "https://squareup.com/pay-invoice/inv-1"
    method, url = provider.session.request.call_args.args
    assert method == "POST"
    assert url.endswith("/v2/invoices/search")
    assert provider.session.request.call_args.kwargs["json"] == {
        "query": {"filter": {"location_ids": ["LOC-123"], "customer_ids": ["CUST-1"]}},
        "limit": 7,
    }


def test_square_list_invoices_needs_a_customer():
    provider = square_provider()
    provider.session.request = Mock()

    with pytest.raises(PaymentValidationError):
        provider.list_invoices("")

    provider.session.request.assert_not_called()
