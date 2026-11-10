"""Stripe Identity webhooks are only verified against a configured secret."""

import hashlib
import hmac
import json
import time
from unittest.mock import patch

import pytest

pytest.importorskip("stripe")

from swap_layer.identity.verification.adapter import IdentityVerificationError  # noqa: E402
from swap_layer.identity.verification.providers.stripe import (  # noqa: E402
    StripeIdentityVerificationProvider,
)

PAYLOAD = json.dumps(
    {"id": "evt_1", "object": "event", "type": "identity.verification_session.verified", "data": {"object": {}}}
).encode("utf-8")


def stripe_signature(secret: str, payload: bytes = PAYLOAD) -> str:
    timestamp = int(time.time())
    signed = f"{timestamp}.".encode() + payload
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


@pytest.mark.parametrize("secret", [None, ""])
def test_missing_webhook_secret_rejects_before_verification(secret):
    provider = StripeIdentityVerificationProvider(secret_key="sk_test_identity", webhook_secret=secret)
    with patch.object(provider._client, "construct_event") as construct_event:
        with pytest.raises(IdentityVerificationError, match="not configured"):
            # A signature made with an empty key must not verify.
            provider.handle_webhook(PAYLOAD, stripe_signature(""))
    construct_event.assert_not_called()


def test_configured_webhook_secret_verifies_signature():
    provider = StripeIdentityVerificationProvider(
        secret_key="sk_test_identity", webhook_secret="whsec_test_identity"
    )
    event = provider.handle_webhook(PAYLOAD, stripe_signature("whsec_test_identity"))
    assert event["id"] == "evt_1"
    with pytest.raises(IdentityVerificationError, match="Invalid signature"):
        provider.handle_webhook(PAYLOAD, stripe_signature("whsec_other"))
