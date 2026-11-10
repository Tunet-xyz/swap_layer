from datetime import datetime
from typing import Any

from swap_layer._compat import legacy_setting
from swap_layer.http import DEFAULT_TIMEOUT

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
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize Twilio SMS provider.

        Args:
            account_sid: Twilio Account SID (falls back to settings.TWILIO_ACCOUNT_SID)
            auth_token: Twilio Auth Token (falls back to settings.TWILIO_AUTH_TOKEN)
            from_number: Twilio phone number (falls back to settings.TWILIO_FROM_NUMBER)
            timeout: Seconds to wait for each Twilio API request
        """
        try:
            from twilio.http.http_client import TwilioHttpClient
            from twilio.rest import Client

            # Use provided config or fallback to Django settings for backward compatibility
            if account_sid is None:
                account_sid = legacy_setting("TWILIO_ACCOUNT_SID")
            if auth_token is None:
                auth_token = legacy_setting("TWILIO_AUTH_TOKEN")
            if from_number is None:
                from_number = legacy_setting("TWILIO_FROM_NUMBER")

            if not account_sid or not auth_token:
                raise ValueError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be configured")

            # Twilio's default HTTP client waits indefinitely; bound every request.
            self.client = Client(
                account_sid, auth_token, http_client=TwilioHttpClient(timeout=timeout)
            )
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
            filters: dict[str, Any] = {"limit": limit}

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

    _OPT_OUT_NOTE = (
        "Twilio has no API to change a number's opt-out state; it applies STOP and "
        "START replies itself. Record opt-outs in your application and skip those numbers."
    )

    def opt_out_number(self, phone_number: str) -> dict[str, Any]:
        """
        Report that Twilio cannot opt a number out through its API.

        Nothing changes at Twilio, so the status is ``not_supported``.
        """
        return {"phone_number": phone_number, "status": "not_supported", "note": self._OPT_OUT_NOTE}

    def opt_in_number(self, phone_number: str) -> dict[str, Any]:
        """
        Report that Twilio cannot opt a number back in through its API.

        Nothing changes at Twilio, so the status is ``not_supported``.
        """
        return {"phone_number": phone_number, "status": "not_supported", "note": self._OPT_OUT_NOTE}
