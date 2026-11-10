"""Caller-supplied identifiers stay inside one URL path segment or Lucene phrase."""

from unittest.mock import Mock, patch

import pytest
import requests

from swap_layer.http import quote_path_segment

TRAVERSAL = "../organizations/org_1/members"


@pytest.mark.parametrize(
    ("value", "encoded"),
    [
        ("auth0|123", "auth0%7C123"),
        ("google-oauth2|1|2", "google-oauth2%7C1%7C2"),
        (TRAVERSAL, "..%2Forganizations%2Forg_1%2Fmembers"),
        ("id?admin=true#frag", "id%3Fadmin%3Dtrue%23frag"),
        ("a b%2F", "a%20b%252F"),
        ("rol_abc.v2", "rol_abc.v2"),
        (12345, "12345"),
    ],
)
def test_identifiers_become_one_path_segment(value, encoded):
    assert quote_path_segment(value) == encoded


@pytest.mark.parametrize("value", [None, "", ".", "..", "..."])
def test_empty_and_dot_identifiers_are_rejected(value):
    with pytest.raises(ValueError):
        quote_path_segment(value)


def test_encoded_segment_survives_url_normalisation():
    url = "https://tenant.example/api/v2/users/" + quote_path_segment(TRAVERSAL)
    prepared = requests.Request("DELETE", url).prepare()
    assert prepared.url == "https://tenant.example/api/v2/users/..%2Forganizations%2Forg_1%2Fmembers"
    unencoded = requests.Request("DELETE", "https://tenant.example/api/v2/users/" + TRAVERSAL).prepare()
    assert "/users/" not in unencoded.url  # what an unencoded identifier would reach


@pytest.fixture
def auth0():
    pytest.importorskip("django")
    from swap_layer.identity.platform.providers.auth0.management.client import Auth0ManagementClient

    client = Auth0ManagementClient(app_name="developer")
    client._make_request = Mock(return_value={})
    return client


def endpoints(mock):
    return [call.args[1] for call in mock.call_args_list]


def test_auth0_user_role_and_org_paths_are_encoded(auth0):
    auth0.users.get_user("auth0|123")
    auth0.users.update_user(TRAVERSAL, email="a@example.com")
    auth0.users.delete_user("auth0|123")
    auth0.organizations.get_organization(TRAVERSAL)
    auth0._make_request.return_value = []
    auth0.roles.get_user_roles("auth0|123")
    auth0.organizations.get_organization_member_roles("org/1", "auth0|123")
    assert endpoints(auth0._make_request) == [
        "/users/auth0%7C123",
        "/users/..%2Forganizations%2Forg_1%2Fmembers",
        "/users/auth0%7C123",
        "/organizations/..%2Forganizations%2Forg_1%2Fmembers",
        "/users/auth0%7C123/roles",
        "/organizations/org%2F1/members/auth0%7C123/roles",
    ]


def test_auth0_rejects_dot_identifiers_without_a_request(auth0):
    with pytest.raises(ValueError):
        auth0.users.delete_user("..")
    auth0._make_request.assert_not_called()


def test_auth0_user_logs_quote_the_user_id_as_one_phrase(auth0):
    auth0._make_request.return_value = []
    auth0.logs.get_user_logs('x" OR type:s OR user_id:"y\\')
    params = auth0._make_request.call_args.kwargs["params"]
    assert params["q"] == 'user_id:"x\\" OR type:s OR user_id:\\"y\\\\"'


@pytest.mark.parametrize("log_type", ["s OR user_id:*", "f)", "", "s\n"])
def test_auth0_log_type_must_be_a_code(auth0, log_type):
    with pytest.raises(ValueError):
        auth0.logs.get_logs_by_type(log_type)
    auth0._make_request.assert_not_called()


def test_auth0_log_type_and_dates_accept_documented_forms(auth0):
    auth0._make_request.return_value = []
    auth0.logs.get_logs_by_type("gd_send_sms")
    auth0.logs.get_logs_by_date_range("2024-01-01", "2024-01-31T23:59:59.999Z")
    auth0.logs.get_logs_by_date_range("20240101", "*")
    queries = [call.kwargs["params"]["q"] for call in auth0._make_request.call_args_list]
    assert queries == [
        "type:gd_send_sms",
        "date:[2024-01-01 TO 2024-01-31T23:59:59.999Z]",
        "date:[20240101 TO *]",
    ]


@pytest.mark.parametrize(
    ("date_from", "date_to"),
    [("2024-01-01] OR type:s OR date:[*", "*"), ("2024-01-01", "2024-01-31 OR x"), ("yesterday", "*")],
)
def test_auth0_log_dates_cannot_extend_the_query(auth0, date_from, date_to):
    with pytest.raises(ValueError):
        auth0.logs.get_logs_by_date_range(date_from, date_to)
    auth0._make_request.assert_not_called()


def test_workos_management_paths_are_encoded():
    from swap_layer.identity.platform.providers.workos.management.client import (
        WorkOSManagementClient,
    )

    client = WorkOSManagementClient(api_key="sk_test")
    client._make_request = Mock(return_value={})
    client.users.get_user(TRAVERSAL)
    client.organizations.delete_organization("org/1")
    assert endpoints(client._make_request) == [
        "/user_management/users/..%2Forganizations%2Forg_1%2Fmembers",
        "/organizations/org%2F1",
    ]


def test_square_and_paypal_paths_are_encoded():
    from swap_layer.billing.providers.paypal import PayPalPaymentProvider
    from swap_layer.billing.providers.square import SquarePaymentProvider

    square = SquarePaymentProvider(access_token="token", location_id="LOC")
    with patch.object(square, "_request", return_value={}) as request:
        square.get_customer("../payments/PAY-1")
    assert request.call_args.args[1] == "/v2/customers/..%2Fpayments%2FPAY-1"

    paypal = PayPalPaymentProvider(client_id="id", client_secret="secret")
    with patch.object(paypal, "_request", return_value={"id": "I-1"}) as request:
        paypal.get_subscription("I-1/cancel")
    assert request.call_args.args[1] == "/v1/billing/subscriptions/I-1%2Fcancel"
