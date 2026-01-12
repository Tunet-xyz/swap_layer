from datetime import datetime
from typing import Any

from django.conf import settings

from ..adapter import (
    SMSInvalidPhoneNumberError,
    SMSMessageNotFoundError,
    SMSProviderAdapter,
    SMSSendError,
)


class TwilioSMSProvider(SMSProviderAdapter):
    """
    Twilio SMS provider implementation.

    Requires:
        pip install twilio

    Configuration in settings.py:
        TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
        TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
        TWILIO_FROM_NUMBER = os.environ.get('TWILIO_FROM_NUMBER')  # E.164 format
    """

    def __init__(
        self,
        account_sid: str | None = None,
        auth_token: str | None = None,
        from_number: str | None = None,
    ):
        """
        Initialize Twilio SMS provider.

        Args:
            account_sid: Twilio Account SID (falls back to settings.TWILIO_ACCOUNT_SID)
            auth_token: Twilio Auth Token (falls back to settings.TWILIO_AUTH_TOKEN)
            from_number: Twilio phone number (falls back to settings.TWILIO_FROM_NUMBER)
        """
        try:
            from twilio.rest import Client

            # Use provided config or fallback to Django settings for backward compatibility
            if account_sid is None:
                account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
            if auth_token is None:
                auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
            if from_number is None:
                from_number = getattr(settings, "TWILIO_FROM_NUMBER", None)

            if not account_sid or not auth_token:
                raise ValueError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be configured")

            self.client = Client(account_sid, auth_token)
            self.from_number = from_number

        except ImportError:
            raise ImportError("Twilio library not installed. Run: pip install twilio")

    def send_sms(
        self,
        to: str,
        message: str,
        from_number: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an SMS message via Twilio."""
        try:
            from_num = from_number or self.from_number
            if not from_num:
                raise SMSSendError("No from_number provided and no default configured")

            # Send message
            tw_message = self.client.messages.create(
                body=message,
                from_=from_num,
                to=to,
                status_callback=metadata.get("status_callback") if metadata else None,
            )

            return {
                "message_id": tw_message.sid,
                "status": tw_message.status,
                "to": tw_message.to,
                "from_number": tw_message.from_,
                "segments": tw_message.num_segments,
            }
        except Exception as e:
            raise SMSSendError(f"Failed to send SMS: {str(e)}")

    def send_bulk_sms(
        self,
        recipients: list[dict[str, str]],
        message: str,
        from_number: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send SMS messages to multiple recipients via Twilio."""
        total_sent = 0
        total_failed = 0
        failed_recipients = []

        for recipient in recipients:
            try:
                to = recipient["to"]
                msg = recipient.get("message", message)
                self.send_sms(to, msg, from_number, metadata)
                total_sent += 1
            except Exception as e:
                total_failed += 1
                failed_recipients.append(
                    {
                        "to": recipient["to"],
                        "error": str(e),
                    }
                )

        return {
            "total_sent": total_sent,
            "total_failed": total_failed,
            "failed_recipients": failed_recipients,
        }

    def get_message_status(self, message_id: str) -> dict[str, Any]:
        """Get the delivery status of a sent message."""
        try:
            message = self.client.messages(message_id).fetch()

            return {
                "message_id": message.sid,
                "status": message.status,
                "to": message.to,
                "from_number": message.from_,
                "error": message.error_message if message.error_code else None,
            }
        except Exception as e:
            if "not found" in str(e).lower():
                raise SMSMessageNotFoundError(f"Message not found: {message_id}")
            raise SMSSendError(f"Failed to get message status: {str(e)}")

    def validate_phone_number(self, phone_number: str) -> dict[str, Any]:
        """
        Validate and get information about a phone number using Twilio Lookup API.

        Note: This requires the Lookup API to be enabled on your Twilio account.
        """
        try:
            lookup = self.client.lookups.v1.phone_numbers(phone_number).fetch()

            return {
                "is_valid": True,
                "phone_number": lookup.phone_number,
                "country_code": lookup.country_code,
                "carrier": None,  # Requires carrier lookup add-on
                "line_type": None,  # Requires carrier lookup add-on
            }
        except Exception as e:
            if "not found" in str(e).lower() or "invalid" in str(e).lower():
                return {
                    "is_valid": False,
                    "phone_number": phone_number,
                    "country_code": None,
                    "carrier": None,
                    "line_type": None,
                }
            raise SMSInvalidPhoneNumberError(f"Failed to validate phone number: {str(e)}")

    def get_account_balance(self) -> dict[str, Any]:
        """Get the Twilio account balance."""
        try:
            balance = self.client.balance.fetch()

            return {
                "balance": float(balance.balance),
                "currency": balance.currency,
                "account_status": "active",
            }
        except Exception as e:
            raise SMSSendError(f"Failed to get account balance: {str(e)}")

    def list_messages(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """List sent messages from Twilio."""
        try:
            # Build filter parameters
            filters = {"limit": limit}

            if start_date:
                filters["date_sent_after"] = datetime.fromisoformat(start_date)

            if end_date:
                filters["date_sent_before"] = datetime.fromisoformat(end_date)

            messages = self.client.messages.list(**filters)

            result = []
            for msg in messages:
                # Filter by status if provided
                if status and msg.status != status:
                    continue

                result.append(
                    {
                        "message_id": msg.sid,
                        "to": msg.to,
                        "from_number": msg.from_,
                        "status": msg.status,
                        "sent_at": msg.date_sent.isoformat() if msg.date_sent else None,
                    }
                )

            return result
        except Exception as e:
            raise SMSSendError(f"Failed to list messages: {str(e)}")

    def opt_out_number(self, phone_number: str) -> dict[str, Any]:
        """
        Add a phone number to the opt-out list.

        Note: Twilio handles opt-outs automatically via STOP/START keywords.
        This is a placeholder for manual opt-out management.
        """
        # In a real implementation, you would store this in your database
        # Twilio automatically handles STOP/START keywords
        return {
            "phone_number": phone_number,
            "status": "opted_out",
        }

    def opt_in_number(self, phone_number: str) -> dict[str, Any]:
        """
        Remove a phone number from the opt-out list.

        Note: Twilio handles opt-ins automatically via STOP/START keywords.
        This is a placeholder for manual opt-in management.
        """
        # In a real implementation, you would remove this from your database
        # Twilio automatically handles STOP/START keywords
        return {
            "phone_number": phone_number,
            "status": "opted_in",
        }
