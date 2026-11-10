"""Every SwapLayer service error is a SwapLayerError and keeps its message."""

import pickle

import pytest

from swap_layer import SwapLayerError
from swap_layer.billing.adapter import (
    PaymentConnectionError,
    PaymentDeclinedError,
    PaymentError,
    PaymentValidationError,
    ResourceNotFoundError,
)
from swap_layer.communications.email.adapter import EmailSendError, TemplateNotFoundError
from swap_layer.communications.sms.adapter import (
    SMSError,
    SMSInvalidPhoneNumberError,
    SMSMessageNotFoundError,
    SMSSendError,
)
from swap_layer.identity.platform.adapter import IdentityPlatformError, OAuthStateError
from swap_layer.identity.verification.adapter import (
    IdentityVerificationConnectionError,
    IdentityVerificationError,
    IdentityVerificationSessionNotFoundError,
    IdentityVerificationValidationError,
)
from swap_layer.storage.adapter import (
    StorageCopyError,
    StorageDeleteError,
    StorageDownloadError,
    StorageError,
    StorageFileNotFoundError,
    StorageMoveError,
    StorageUploadError,
)

ERRORS = [
    PaymentError, PaymentValidationError, PaymentDeclinedError, PaymentConnectionError,
    ResourceNotFoundError, EmailSendError, TemplateNotFoundError, SMSError, SMSSendError,
    SMSMessageNotFoundError, SMSInvalidPhoneNumberError, IdentityPlatformError, OAuthStateError,
    IdentityVerificationError, IdentityVerificationValidationError,
    IdentityVerificationSessionNotFoundError, IdentityVerificationConnectionError, StorageError,
    StorageUploadError, StorageDownloadError, StorageFileNotFoundError, StorageDeleteError,
    StorageCopyError, StorageMoveError,
]


@pytest.mark.parametrize("error_class", ERRORS)
def test_service_errors_share_the_package_root(error_class):
    assert issubclass(error_class, SwapLayerError)
    error = error_class("something failed")
    assert str(error) == "something failed"
    assert error.args == ("something failed",)
    copy = pickle.loads(pickle.dumps(error))
    assert type(copy) is error_class and str(copy) == "something failed"
    assert str(error_class()) == ""
    with pytest.raises(SwapLayerError):
        raise error


def test_existing_except_clauses_still_match():
    with pytest.raises(PaymentError):
        raise PaymentValidationError("bad amount")
    with pytest.raises(StorageError):
        raise StorageFileNotFoundError("missing")
    with pytest.raises(Exception):  # noqa: B017
        raise SMSSendError("failed")
