from typing import Dict, Any, Optional, List
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
        to: List[str],
        subject: str,
        text_body: Optional[str] = None,
        html_body: Optional[str] = None,
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        template_id: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
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
            )

            if html_body:
                msg.attach_alternative(html_body, "text/html")

            if attachments:
                for attachment in attachments:
                    # Expecting dict with 'filename', 'content', 'mimetype'
                    msg.attach(
                        attachment.get('filename'),
                        attachment.get('content'),
                        attachment.get('mimetype')
                    )

            # Support for Anymail-specific features via esp_extra if available
            if metadata:
                # This is the standard way to pass metadata to Anymail backends
                msg.extra_headers = metadata
                # Anymail uses 'tags' or 'metadata' attribute on the message object
                # We can try to set it if the attribute exists (duck typing)
                if hasattr(msg, 'metadata'):
                    msg.metadata = metadata
                if hasattr(msg, 'tags') and 'tags' in metadata:
                    msg.tags = metadata['tags']

            msg.send()
            
            return {
                "status": "sent",
                "message_id": getattr(msg, 'anymail_status', {}).get('message_id') or "sent-via-django",
            }

        except Exception as e:
            raise EmailSendError(f"Failed to send email: {str(e)}") from e
