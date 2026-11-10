"""Email providers without signed webhooks never report a payload as verified."""

import pytest

from swap_layer.communications.email.providers.django_email import DjangoEmailAdapter
from swap_layer.communications.email.providers.smtp import SMTPEmailProvider


@pytest.mark.parametrize("provider_class", [SMTPEmailProvider, DjangoEmailAdapter])
@pytest.mark.parametrize("signature", ["", "forged", "sha256=anything"])
def test_unsigned_providers_reject_every_webhook(provider_class, signature):
    provider = provider_class()
    assert provider.validate_webhook_signature(b'{"event": "delivered"}', signature) is False
    assert provider.validate_webhook_signature(b"", signature, timestamp="1700000000") is False
