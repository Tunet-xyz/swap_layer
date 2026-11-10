"""WorkOS sign-in callbacks must return a state issued to the same session."""

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("workos")

from swap_layer.identity.platform.adapter import OAuthStateError  # noqa: E402
from swap_layer.identity.platform.providers.workos import client as workos_client  # noqa: E402
from swap_layer.identity.platform.providers.workos.client import (  # noqa: E402
    STATE_SESSION_KEY,
    WorkOSClient,
)


@pytest.fixture
def workos():
    with patch.object(workos_client, "WorkOSSDKClient") as sdk:
        provider = WorkOSClient(app_name="default")
        sdk.return_value.user_management.authenticate_with_code.return_value = MagicMock(
            sealed_session="sealed"
        )
        yield provider, sdk.return_value.user_management


def request(session, state=None, method="GET"):
    req = MagicMock()
    req.session = session
    req.method = method
    params = {} if state is None else {"state": state, "code": "abc"}
    req.GET, req.POST = (params, {}) if method == "GET" else ({}, params)
    return req


def issued_state(provider, management, session, state=None):
    provider.get_authorization_url(request(session), "https://app.example/callback", state=state)
    return management.get_authorization_url.call_args.kwargs["state"]


def test_generated_state_is_random_and_verified_once(workos):
    provider, management = workos
    session: dict = {}
    first = issued_state(provider, management, session)
    second = issued_state(provider, management, session)
    assert first != second and len(first) >= 40
    provider.exchange_code_for_user(request(session, first), "abc")
    management.authenticate_with_code.assert_called_once_with(code="abc")
    with pytest.raises(OAuthStateError):
        provider.exchange_code_for_user(request(session, first), "abc")  # replay
    provider.exchange_code_for_user(request(session, second, method="POST"), "abc")


@pytest.mark.parametrize("state", [None, "", "forged"])
def test_missing_or_unknown_state_is_rejected(workos, state):
    provider, management = workos
    session: dict = {}
    issued_state(provider, management, session)
    with pytest.raises(OAuthStateError):
        provider.exchange_code_for_user(request(session, state), "abc")
    management.authenticate_with_code.assert_not_called()


def test_state_from_another_session_is_rejected(workos):
    provider, management = workos
    state = issued_state(provider, management, {})
    with pytest.raises(OAuthStateError):
        provider.exchange_code_for_user(request({}, state), "abc")


def test_expired_state_is_rejected(workos):
    provider, management = workos
    session: dict = {}
    state = issued_state(provider, management, session, state="caller-state")
    assert state == "caller-state"
    with patch.object(workos_client.time, "time", return_value=10**12):
        with pytest.raises(OAuthStateError):
            provider.exchange_code_for_user(request(session, state), "abc")


def test_pending_states_are_bounded_and_cleared(workos):
    provider, management = workos
    session: dict = {}
    for _ in range(workos_client.MAX_PENDING_STATES + 5):
        issued_state(provider, management, session)
    assert len(session[STATE_SESSION_KEY]) == workos_client.MAX_PENDING_STATES
    session["workos_sealed_session"] = "sealed"
    provider.clear_session(request(session))
    assert session == {}
