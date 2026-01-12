from abc import ABC, abstractmethod
from typing import Any


class IdentityVerificationError(Exception):
    """Base exception for all identity verification related errors."""

    pass


class IdentityVerificationValidationError(IdentityVerificationError):
    """Raised when input data is invalid."""

    pass


class IdentityVerificationSessionNotFoundError(IdentityVerificationError):
    """Raised when a verification session is not found."""

    pass


class IdentityVerificationConnectionError(IdentityVerificationError):
    """Raised when connection to the verification provider fails."""

    pass


class IdentityVerificationProviderAdapter(ABC):
    """
    Abstract base class for Identity Verification Providers (Stripe, Onfido, etc.)
    This ensures we can switch providers without rewriting the application logic.
    """

    @abstractmethod
    def get_vendor_client(self) -> Any:
        """
        Return the underlying vendor client/SDK for advanced usage.
        Use this escape hatch when you need to access provider-specific features
        that are not exposed by the abstraction layer.
        """
        pass

    @abstractmethod
    def create_verification_session(
        self, user: Any, verification_type: str, options: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Create a verification session with the provider.

        Args:
            user: The user to verify.
            verification_type: Type of verification (e.g., 'document').
            options: Provider-specific options.

        Returns:
            Dict containing session details with keys:
            - provider_session_id: str
            - client_secret: str
            - status: str
            - type: str
            - url: str (optional)
            - created: int (timestamp)

        Raises:
            IdentityVerificationValidationError: If data is invalid
            IdentityVerificationConnectionError: If provider is unreachable
        """
        pass

    @abstractmethod
    def get_verification_session(self, session_id: str) -> dict[str, Any]:
        """
        Retrieve session details from the provider.

        Args:
            session_id: The provider's session ID

        Returns:
            Dict with keys: id, status, type, created, metadata,
            verified_outputs (optional), last_error (optional)

        Raises:
            IdentityVerificationSessionNotFoundError: If session doesn't exist
        """
        pass

    @abstractmethod
    def list_verification_sessions(
        self, limit: int = 10, status: str | None = None, **kwargs
    ) -> dict[str, Any]:
        """
        List verification sessions from the provider.

        Args:
            limit: Maximum number of results
            status: Optional status filter
            **kwargs: Provider-specific filters

        Returns:
            Dict with session data
        """
        pass

    @abstractmethod
    def cancel_verification_session(self, session_id: str) -> dict[str, Any]:
        """
        Cancel a verification session.

        Args:
            session_id: The provider's session ID

        Returns:
            Dict with keys: id, status

        Raises:
            IdentityVerificationSessionNotFoundError: If session doesn't exist
        """
        pass

    @abstractmethod
    def redact_verification_session(self, session_id: str) -> dict[str, Any]:
        """
        Redact a verification session to remove PII data.

        Args:
            session_id: The provider's session ID

        Returns:
            Dict with keys: id, status

        Raises:
            IdentityVerificationSessionNotFoundError: If session doesn't exist
        """
        pass

    @abstractmethod
    def get_verification_report(self, report_id: str) -> dict[str, Any]:
        """
        Retrieve a verification report.

        Args:
            report_id: The provider's report ID

        Returns:
            Dict with report details

        Raises:
            IdentityVerificationSessionNotFoundError: If report doesn't exist
        """
        pass

    @abstractmethod
    def get_verification_insights(self, session_id: str) -> dict[str, Any]:
        """
        Get insights from a verification session.

        Args:
            session_id: The provider's session ID

        Returns:
            Dict with keys:
            - session_id: str
            - status: str
            - verified_outputs: dict (optional)
            - checks_performed: list of dicts with type, status, error
            - risk_signals: list (optional)
        """
        pass

    @abstractmethod
    def handle_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        """
        Verify and parse a webhook payload.

        Args:
            payload: Raw webhook payload
            signature: Webhook signature for verification

        Returns:
            Dict with parsed event data

        Raises:
            IdentityVerificationError: If signature verification fails
        """
        pass
