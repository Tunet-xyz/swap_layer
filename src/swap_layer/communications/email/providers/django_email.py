from typing import Any

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from ..adapter import EmailProviderAdapter, EmailSendError


class DjangoEmailAdapter(EmailProviderAdapter):
    """
    Email provider that wraps Django's standard email backend.
    This allows using any backend supported by Django or django-anymail
    (SMTP, SendGrid, Mailgun, SES, Postmark, etc.) configured via settings.
    """

    def send_email(
        self,
        to: list[str],
        subject: str,
        text_body: str | None = None,
        html_body: str | None = None,
        from_email: str | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        reply_to: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
        metadata: dict[str, Any] | None = None,
        template_id: str | None = None,
        template_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            # If template_id is provided, we assume it's a Django template path
            # For provider-specific templates (e.g. SendGrid dynamic templates),
            # one would typically use the 'metadata' or specific Anymail headers,
            # but here we standardize on Django templates for portability.
            if template_id and not html_body:
                context = template_data or {}
                html_body = render_to_string(template_id, context)
                # Simple text fallback if not provided
                if not text_body:
                    text_body = "Please view this email in a modern email client."

            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=from_email,
                to=to,
                cc=cc,
                bcc=bcc,
                reply_to=[reply_to] if reply_to else None,
                headers=headers,
            )

            if html_body:
                msg.attach_alternative(html_body, "text/html")

            if attachments:
                for attachment in attachments:
                    # Expecting dict with 'filename', 'content', 'mimetype'
                    msg.attach(
                        attachment.get("filename"),
                        attachment.get("content"),
                        attachment.get("mimetype"),
                    )

            # Support for Anymail-specific features via esp_extra if available
            if metadata:
                # This is the standard way to pass metadata to Anymail backends
                msg.extra_headers = metadata
                # Anymail uses 'tags' or 'metadata' attribute on the message object
                # We can try to set it if the attribute exists (duck typing)
                if hasattr(msg, "metadata"):
                    msg.metadata = metadata
                if hasattr(msg, "tags") and "tags" in metadata:
                    msg.tags = metadata["tags"]

            msg.send()

            return {
                "status": "sent",
                "message_id": getattr(msg, "anymail_status", {}).get("message_id")
                or "sent-via-django",
            }

        except Exception as e:
            raise EmailSendError(f"Failed to send email: {str(e)}") from e

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
        Send a template email.
        Calls send_email with template_id and template_data.
        """
        # Convert list reply_to to string if needed by send_email (which seems to take string?)
        # Actually send_email in this file takes reply_to: Optional[str] based on my read
        # But abstraction layer might enforce list?
        # The abstraction layer defines reply_to as Optional[List[str]].
        # This implementation's send_email takes reply_to: Optional[str].
        # We need to bridge this gap.

        reply_to_str = reply_to[0] if reply_to else None

        return self.send_email(
            to=to,
            subject=template_data.get("subject", ""),
            template_id=template_id,
            template_data=template_data,
            from_email=from_email,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to_str,  # type: ignore
            metadata=metadata,
        )

    def send_bulk_email(
        self,
        recipients: list[dict[str, Any]],
        subject: str,
        text_body: str | None = None,
        html_body: str | None = None,
        from_email: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Simple loop implementation since Django generic backend doesn't support bulk."""
        sent = 0
        failed = 0
        failed_list = []

        for r in recipients:
            try:
                self.send_email(
                    to=[r["to"]],
                    subject=subject,
                    text_body=text_body,
                    html_body=html_body,
                    from_email=from_email,
                    metadata=metadata,
                )
                sent += 1
            except Exception:
                failed += 1
                failed_list.append(r["to"])

        return {"total_sent": sent, "total_failed": failed, "failed_recipients": failed_list}

    def verify_email(self, email: str) -> dict[str, Any]:
        raise NotImplementedError("Not supported by generic Django backend")

    def get_send_statistics(
        self, start_date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        raise NotImplementedError("Not supported by generic Django backend")

    def add_to_suppression_list(self, email: str, reason: str = "manual") -> dict[str, Any]:
        raise NotImplementedError("Not supported by generic Django backend")

    def remove_from_suppression_list(self, email: str) -> dict[str, Any]:
        raise NotImplementedError("Not supported by generic Django backend")

    def validate_webhook_signature(
        self, payload: bytes, signature: str, timestamp: str | None = None
    ) -> bool:
        return False
