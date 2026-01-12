import logging
import re
import uuid
from string import Template
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.mail.message import EmailMessage

from ..adapter import EmailProviderAdapter, EmailSendError, TemplateNotFoundError

logger = logging.getLogger(__name__)


class SMTPEmailProvider(EmailProviderAdapter):
    """
    SMTP Email Provider using Django's default email backend.

    This provider wraps Django's built-in email functionality and provides
    a consistent interface with other email providers.

    Configuration (in settings.py):
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        EMAIL_HOST = 'smtp.gmail.com'
        EMAIL_PORT = 587
        EMAIL_USE_TLS = True
        EMAIL_HOST_USER = 'your-email@gmail.com'
        EMAIL_HOST_PASSWORD = 'your-password'
        DEFAULT_FROM_EMAIL = 'noreply@example.com'
    """

    def __init__(self):
        self.default_from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")
        self.connection = None

    def _get_connection(self):
        """Get or create email backend connection."""
        if self.connection is None:
            self.connection = get_connection()
        return self.connection

    def send_email(
        self,
        to: list[str],
        subject: str,
        text_body: str | None = None,
        html_body: str | None = None,
        from_email: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        reply_to: list[str] | None = None,
        attachments: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send an email using Django's SMTP backend.

        Returns:
            Dict with message_id, status, and provider_response
        """
        try:
            from_addr = from_email or self.default_from_email

            # Validate inputs
            if not to:
                raise EmailSendError("At least one recipient is required")
            if not subject:
                raise EmailSendError("Subject is required")
            if not text_body and not html_body:
                raise EmailSendError("Either text_body or html_body is required")

            # Create email message
            if html_body:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_body or "",
                    from_email=from_addr,
                    to=to,
                    cc=cc or [],
                    bcc=bcc or [],
                    reply_to=reply_to or [],
                    headers=headers or {},
                )
                msg.attach_alternative(html_body, "text/html")
            else:
                msg = EmailMessage(
                    subject=subject,
                    body=text_body,
                    from_email=from_addr,
                    to=to,
                    cc=cc or [],
                    bcc=bcc or [],
                    reply_to=reply_to or [],
                    headers=headers or {},
                )

            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    msg.attach(
                        filename=attachment.get("filename", "attachment"),
                        content=attachment.get("content", ""),
                        mimetype=attachment.get("mimetype", "application/octet-stream"),
                    )

            # Send email
            result = msg.send(fail_silently=False)

            # Generate a unique message ID (Django doesn't provide one)
            message_id = f"smtp_{uuid.uuid4().hex}"

            logger.info(f"Email sent via SMTP to {to}: {subject}")

            return {
                "message_id": message_id,
                "status": "sent" if result == 1 else "failed",
                "provider_response": {
                    "sent_count": result,
                    "backend": "smtp",
                },
            }

        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            raise EmailSendError(f"Failed to send email: {str(e)}")

    def send_template_email(
        self,
        to: list[str],
        template_id: str,
        template_data: dict[str, Any],
        from_email: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        reply_to: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send a template email using Django's template system.

        Note: For SMTP provider, template_id should be a path to a Django template.
        Template data will be used as context for rendering.
        """
        try:
            from django.template import TemplateDoesNotExist
            from django.template.loader import render_to_string

            # Try to render both text and HTML versions
            try:
                html_body = render_to_string(f"{template_id}.html", template_data)
            except TemplateDoesNotExist:
                html_body = None

            try:
                text_body = render_to_string(f"{template_id}.txt", template_data)
            except TemplateDoesNotExist:
                text_body = None

            if not html_body and not text_body:
                raise TemplateNotFoundError(
                    f"Template not found: {template_id}.html or {template_id}.txt"
                )

            # Extract subject from template_data or use a default
            subject = template_data.get("subject", "Email from SwapLayer")

            return self.send_email(
                to=to,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                from_email=from_email,
                cc=cc,
                bcc=bcc,
                reply_to=reply_to,
                metadata=metadata,
            )

        except TemplateNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to send template email: {e}")
            raise EmailSendError(f"Failed to send template email: {str(e)}")

    def send_bulk_email(
        self,
        recipients: list[dict[str, Any]],
        subject: str,
        text_body: str | None = None,
        html_body: str | None = None,
        from_email: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send bulk emails with basic substitution support.

        Note: SMTP doesn't have native bulk sending. This sends individual emails.
        For true bulk sending with personalization, use SendGrid or similar.
        """
        total_sent = 0
        total_failed = 0
        failed_recipients = []

        connection = self._get_connection()

        try:
            connection.open()

            for recipient in recipients:
                to_email = None
                try:
                    to_email = recipient.get("to")
                    if not to_email:
                        raise ValueError("Missing 'to' field in recipient")

                    substitutions = recipient.get("substitutions", {})

                    # Apply simple string substitutions using string.Template for better performance
                    # Note: Using $variable format for consistency with Python's string.Template
                    personalized_subject = (
                        Template(subject).safe_substitute(substitutions) if subject else ""
                    )
                    personalized_text = (
                        Template(text_body).safe_substitute(substitutions) if text_body else None
                    )
                    personalized_html = (
                        Template(html_body).safe_substitute(substitutions) if html_body else None
                    )

                    # Ensure we have at least text_body or html_body
                    if not personalized_text and not personalized_html:
                        raise ValueError("Either text_body or html_body is required")

                    self.send_email(
                        to=[to_email],
                        subject=personalized_subject,
                        text_body=personalized_text,
                        html_body=personalized_html,
                        from_email=from_email,
                        metadata=metadata,
                    )
                    total_sent += 1

                except Exception as e:
                    logger.error(f"Failed to send bulk email to {to_email or 'unknown'}: {e}")
                    total_failed += 1
                    failed_recipients.append({"email": to_email or "unknown", "error": str(e)})

        finally:
            connection.close()

        logger.info(f"Bulk email sent: {total_sent} sent, {total_failed} failed")

        return {
            "total_sent": total_sent,
            "total_failed": total_failed,
            "failed_recipients": failed_recipients,
        }

    def verify_email(self, email: str) -> dict[str, Any]:
        """
        Basic email validation (SMTP doesn't support verification).

        Returns a simple format check. For real verification, use SendGrid or similar.
        """
        # Basic email regex pattern
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        is_valid = bool(re.match(email_pattern, email))

        return {
            "is_valid": is_valid,
            "reason": "format_check" if is_valid else "invalid_format",
            "provider_response": {
                "method": "regex",
                "note": "SMTP provider only performs basic format validation",
            },
        }

    def get_send_statistics(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Get statistics (not supported by SMTP).

        SMTP doesn't track statistics. Returns zero values.
        For statistics, use SendGrid, Mailgun, or AWS SES.
        """
        logger.warning("SMTP provider does not support statistics")

        return {
            "sent": 0,
            "delivered": 0,
            "bounced": 0,
            "complained": 0,
            "opened": 0,
            "clicked": 0,
            "note": "SMTP provider does not track statistics",
        }

    def add_to_suppression_list(
        self,
        email: str,
        reason: str = "manual",
    ) -> dict[str, Any]:
        """
        Add to suppression list (not supported by SMTP).

        SMTP doesn't have a suppression list. This is a no-op.
        For suppression lists, use SendGrid, Mailgun, or AWS SES.
        """
        logger.warning(f"SMTP provider does not support suppression lists: {email}")

        return {
            "email": email,
            "status": "not_supported",
            "reason": reason,
            "note": "SMTP provider does not support suppression lists",
        }

    def remove_from_suppression_list(self, email: str) -> dict[str, Any]:
        """
        Remove from suppression list (not supported by SMTP).
        """
        logger.warning(f"SMTP provider does not support suppression lists: {email}")

        return {
            "email": email,
            "status": "not_supported",
            "note": "SMTP provider does not support suppression lists",
        }

    def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: str | None = None,
    ) -> bool:
        """
        Validate webhook signature (not applicable for SMTP).

        SMTP doesn't have webhooks. Always returns True.
        """
        logger.warning("SMTP provider does not support webhooks")
        return True
