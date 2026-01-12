from abc import ABC, abstractmethod
from typing import Any


class SMSProviderAdapter(ABC):
    """
    Abstract base class for SMS Providers (Twilio, AWS SNS, Vonage, etc.)
    This ensures we can switch providers without rewriting the application logic.
    """

    @abstractmethod
    def send_sms(
        self,
        to: str,
        message: str,
        from_number: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send an SMS message.

        Args:
            to: Recipient phone number in E.164 format (e.g., +14155552671)
            message: Message content (max length varies by provider)
            from_number: Sender phone number (uses default if not provided)
            metadata: Provider-specific metadata

        Returns:
            Dict with keys: message_id, status, to, from_number, segments

        Raises:
            SMSSendError: If message sending fails
        """
        pass

    @abstractmethod
    def send_bulk_sms(
        self,
        recipients: list[dict[str, str]],
        message: str,
        from_number: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send SMS messages to multiple recipients.

        Args:
            recipients: List of dicts with 'to' and optional 'message' for personalization
            message: Default message (used if recipient dict doesn't have 'message')
            from_number: Sender phone number
            metadata: Provider-specific metadata

        Returns:
            Dict with keys: total_sent, total_failed, failed_recipients
        """
        pass

    @abstractmethod
    def get_message_status(self, message_id: str) -> dict[str, Any]:
        """
        Get the delivery status of a sent message.

        Args:
            message_id: Message identifier returned from send_sms

        Returns:
            Dict with keys: message_id, status, to, from_number, error (if failed)

        Raises:
            SMSMessageNotFoundError: If message doesn't exist
        """
        pass

    @abstractmethod
    def validate_phone_number(self, phone_number: str) -> dict[str, Any]:
        """
        Validate and get information about a phone number.

        Args:
            phone_number: Phone number to validate

        Returns:
            Dict with keys: is_valid, phone_number, country_code, carrier, line_type
        """
        pass

    @abstractmethod
    def get_account_balance(self) -> dict[str, Any]:
        """
        Get the account balance/credits.

        Returns:
            Dict with keys: balance, currency, account_status
        """
        pass

    @abstractmethod
    def list_messages(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        List sent messages.

        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
            status: Filter by status (sent, delivered, failed, etc.)
            limit: Maximum number of results

        Returns:
            List of message dicts with keys: message_id, to, from_number, status, sent_at
        """
        pass

    @abstractmethod
    def opt_out_number(self, phone_number: str) -> dict[str, Any]:
        """
        Add a phone number to the opt-out list.

        Args:
            phone_number: Phone number to opt out

        Returns:
            Dict with keys: phone_number, status
        """
        pass

    @abstractmethod
    def opt_in_number(self, phone_number: str) -> dict[str, Any]:
        """
        Remove a phone number from the opt-out list.

        Args:
            phone_number: Phone number to opt in

        Returns:
            Dict with keys: phone_number, status
        """
        pass


# Custom Exceptions
class SMSError(Exception):
    """Base exception for SMS operations."""

    pass


class SMSSendError(SMSError):
    """Raised when SMS sending fails."""

    pass


class SMSMessageNotFoundError(SMSError):
    """Raised when a message is not found."""

    pass


class SMSInvalidPhoneNumberError(SMSError):
    """Raised when a phone number is invalid."""

    pass
