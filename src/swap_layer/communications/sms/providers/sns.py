from typing import Any

from ..adapter import SMSProviderAdapter


class SNSSMSProvider(SMSProviderAdapter):
    """
    AWS SNS SMS provider.

    To complete this implementation:
    1. Install boto3: pip install boto3
    2. Configure AWS credentials in settings or environment
    3. Implement all abstract methods using boto3 SNS client

    Configuration needed in settings.py:
        AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
        AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
        AWS_REGION_NAME = os.environ.get('AWS_REGION_NAME', 'us-east-1')
        AWS_SNS_DEFAULT_SENDER_ID = os.environ.get('AWS_SNS_DEFAULT_SENDER_ID')  # Optional
    """

    def __init__(self):
        """Initialize AWS SNS SMS provider."""
        try:
            import boto3
            from django.conf import settings

            aws_access_key_id = getattr(settings, "AWS_ACCESS_KEY_ID", None)
            aws_secret_access_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
            aws_region_name = getattr(settings, "AWS_REGION_NAME", "us-east-1")

            if not aws_access_key_id or not aws_secret_access_key:
                raise ValueError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be configured")

            self.sns_client = boto3.client(
                "sns",
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region_name,
            )
            self.sender_id = getattr(settings, "AWS_SNS_DEFAULT_SENDER_ID", None)

        except ImportError:
            raise ImportError("boto3 library not installed. Run: pip install boto3")

    def send_sms(
        self,
        to: str,
        message: str,
        from_number: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send an SMS message via AWS SNS."""
        from sms.adapter import SMSSendError

        try:
            # Set message attributes
            message_attributes = {
                "AWS.SNS.SMS.SMSType": {
                    "DataType": "String",
                    "StringValue": "Transactional",  # or 'Promotional'
                }
            }

            # Add sender ID if available
            if self.sender_id or from_number:
                message_attributes["AWS.SNS.SMS.SenderID"] = {
                    "DataType": "String",
                    "StringValue": from_number or self.sender_id,
                }

            # Send message
            response = self.sns_client.publish(
                PhoneNumber=to, Message=message, MessageAttributes=message_attributes
            )

            return {
                "message_id": response["MessageId"],
                "status": "sent",  # SNS doesn't provide immediate status
                "to": to,
                "from_number": from_number or self.sender_id,
                "segments": 1,  # SNS doesn't provide segment count
            }
        except Exception as e:
            raise SMSSendError(f"Failed to send SMS via SNS: {str(e)}")

    def send_bulk_sms(
        self,
        recipients: list[dict[str, str]],
        message: str,
        from_number: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send SMS messages to multiple recipients via AWS SNS."""
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
        """
        Get the delivery status of a sent message.

        Note: AWS SNS doesn't directly support message status queries.
        To track message delivery status, you need to:
        1. Set up SNS delivery status logging to CloudWatch Logs
        2. Configure SNS topics with delivery status attributes
        3. Query CloudWatch Logs for the message_id

        This implementation returns a placeholder response.
        For production use, implement CloudWatch Logs integration.
        """

        # This is a placeholder implementation
        # In production, you would query CloudWatch Logs or use SNS delivery status topics
        return {
            "message_id": message_id,
            "status": "unknown",  # SNS doesn't provide direct status lookup
            "to": None,
            "from_number": None,
            "error": "AWS SNS requires CloudWatch Logs integration for status tracking",
        }

    def validate_phone_number(self, phone_number: str) -> dict[str, Any]:
        """
        Validate and get information about a phone number.

        Note: This uses AWS Pinpoint phone number validation API.
        Requires AWS Pinpoint to be enabled in your AWS account.
        """
        from ..adapter import SMSInvalidPhoneNumberError

        try:
            import boto3
            from django.conf import settings

            # Initialize Pinpoint client for phone validation
            aws_access_key_id = getattr(settings, "AWS_ACCESS_KEY_ID", None)
            aws_secret_access_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
            aws_region_name = getattr(settings, "AWS_REGION_NAME", "us-east-1")

            pinpoint_client = boto3.client(
                "pinpoint",
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region_name,
            )

            # Validate phone number
            response = pinpoint_client.phone_number_validate(
                NumberValidateRequest={"PhoneNumber": phone_number}
            )

            result = response.get("NumberValidateResponse", {})

            return {
                "is_valid": result.get("PhoneType") != "INVALID",
                "phone_number": result.get("CleansedPhoneNumberE164", phone_number),
                "country_code": result.get("CountryCodeIso2"),
                "carrier": result.get("Carrier"),
                "line_type": result.get("PhoneType"),
            }
        except Exception as e:
            raise SMSInvalidPhoneNumberError(f"Failed to validate phone number: {str(e)}")

    def get_account_balance(self) -> dict[str, Any]:
        """
        Get the account balance/credits.

        Note: AWS SNS doesn't have a direct balance API.
        To monitor SMS spending, use:
        1. AWS Cost Explorer API
        2. AWS Budgets
        3. CloudWatch metrics for SMS usage

        This implementation returns a placeholder response.
        For production use, integrate with AWS Cost Explorer.
        """
        # Placeholder implementation
        # In production, you would use AWS Cost Explorer or Budgets API
        return {
            "balance": None,  # SNS is pay-as-you-go, no balance concept
            "currency": "USD",
            "account_status": "active",
        }

    def list_messages(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        List sent messages.

        Note: AWS SNS doesn't store message history by default.
        To track sent messages, you need to:
        1. Enable SNS delivery status logging to CloudWatch Logs
        2. Query CloudWatch Logs Insights for message history
        3. Alternatively, maintain your own database of sent messages

        This implementation returns an empty list.
        For production use, implement CloudWatch Logs query or database tracking.
        """
        # Placeholder implementation
        # In production, you would query CloudWatch Logs or your own database
        return []

    def opt_out_number(self, phone_number: str) -> dict[str, Any]:
        """
        Check if a phone number is opted out.

        AWS SNS automatically manages opt-outs when users reply with STOP.
        This method checks if a number is currently opted out.
        """
        from sms.adapter import SMSError

        try:
            response = self.sns_client.check_if_phone_number_is_opted_out(phoneNumber=phone_number)

            is_opted_out = response.get("isOptedOut", False)

            return {
                "phone_number": phone_number,
                "status": "opted_out" if is_opted_out else "active",
            }
        except Exception as e:
            raise SMSError(f"Failed to check opt-out status: {str(e)}")

    def opt_in_number(self, phone_number: str) -> dict[str, Any]:
        """
        Remove a phone number from the opt-out list.

        This allows sending SMS to a number that was previously opted out.
        """
        from sms.adapter import SMSError

        try:
            self.sns_client.opt_in_phone_number(phoneNumber=phone_number)

            return {
                "phone_number": phone_number,
                "status": "opted_in",
            }
        except Exception as e:
            raise SMSError(f"Failed to opt in phone number: {str(e)}")
