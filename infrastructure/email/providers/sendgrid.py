from typing import Dict, Any, Optional, List
from django.conf import settings
import logging
import re
import base64
import json

from ..adapter import EmailProviderAdapter, EmailSendError, TemplateNotFoundError

logger = logging.getLogger(__name__)


class SendGridEmailProvider(EmailProviderAdapter):
    """
    SendGrid Email Provider implementation.
    
    This provider uses the SendGrid API for sending emails with advanced features
    like templates, bulk sending, statistics, and suppression lists.
    
    Configuration (in settings.py):
        EMAIL_PROVIDER = 'sendgrid'
        SENDGRID_API_KEY = 'your-api-key'
        DEFAULT_FROM_EMAIL = 'noreply@example.com'
    
    Dependencies:
        pip install sendgrid
    """

    def __init__(self):
        self.api_key = getattr(settings, 'SENDGRID_API_KEY', None)
        if not self.api_key:
            raise ValueError("SENDGRID_API_KEY is required in settings")
        
        self.default_from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileName, FileType, Disposition
            self.client = SendGridAPIClient(self.api_key)
            self.Mail = Mail
            self.Email = Email
            self.To = To
            self.Content = Content
            self.Attachment = Attachment
            self.FileContent = FileContent
            self.FileName = FileName
            self.FileType = FileType
            self.Disposition = Disposition
        except ImportError:
            raise ImportError(
                "SendGrid package is required. Install it with: pip install sendgrid"
            )

    def send_email(
        self,
        to: List[str],
        subject: str,
        text_body: Optional[str] = None,
        html_body: Optional[str] = None,
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send an email using SendGrid API.
        """
        try:
            from sendgrid.helpers.mail import (
                Mail, Personalization, Cc, Bcc, ReplyTo,
                Header, CustomArg, Content, To
            )
            
            # Validate inputs
            if not to:
                raise EmailSendError("At least one recipient is required")
            if not subject:
                raise EmailSendError("Subject is required")
            if not text_body and not html_body:
                raise EmailSendError("Either text_body or html_body is required")

            from_addr = from_email or self.default_from_email
            
            # Create message
            message = Mail(
                from_email=from_addr,
                to_emails=to,
                subject=subject,
            )
            
            # Add content
            if text_body:
                message.add_content(Content("text/plain", text_body))
            if html_body:
                message.add_content(Content("text/html", html_body))
            
            # Add CC recipients
            if cc:
                personalization = Personalization()
                for recipient in to:
                    personalization.add_to(To(recipient))
                for cc_email in cc:
                    personalization.add_cc(Cc(cc_email))
                message.add_personalization(personalization)
            
            # Add BCC recipients
            if bcc:
                if not message.personalizations:
                    personalization = Personalization()
                    for recipient in to:
                        personalization.add_to(To(recipient))
                    message.add_personalization(personalization)
                for bcc_email in bcc:
                    message.personalizations[0].add_bcc(Bcc(bcc_email))
            
            # Add reply-to
            if reply_to:
                message.reply_to = ReplyTo(reply_to[0])
            
            # Add custom headers
            if headers:
                for key, value in headers.items():
                    message.add_header(Header(key, value))
            
            # Add metadata as custom args
            if metadata:
                for key, value in metadata.items():
                    message.add_custom_arg(CustomArg(key, str(value)))
            
            # Add attachments
            if attachments:
                for attachment_data in attachments:
                    attachment = self.Attachment()
                    
                    # Encode content to base64 if it's bytes
                    content = attachment_data.get('content', b'')
                    if isinstance(content, bytes):
                        encoded_content = base64.b64encode(content).decode()
                    else:
                        encoded_content = base64.b64encode(content.encode()).decode()
                    
                    attachment.file_content = self.FileContent(encoded_content)
                    attachment.file_name = self.FileName(attachment_data.get('filename', 'attachment'))
                    attachment.file_type = self.FileType(attachment_data.get('mimetype', 'application/octet-stream'))
                    attachment.disposition = self.Disposition('attachment')
                    
                    message.add_attachment(attachment)
            
            # Send email
            response = self.client.send(message)
            
            # Extract message ID from headers
            message_id = response.headers.get('X-Message-Id', 'unknown')
            
            logger.info(f"Email sent via SendGrid to {to}: {subject}")
            
            return {
                'message_id': message_id,
                'status': 'sent' if response.status_code in [200, 202] else 'failed',
                'provider_response': {
                    'status_code': response.status_code,
                    'body': response.body,
                    'headers': dict(response.headers),
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to send email via SendGrid: {e}")
            raise EmailSendError(f"Failed to send email: {str(e)}")

    def send_template_email(
        self,
        to: List[str],
        template_id: str,
        template_data: Dict[str, Any],
        from_email: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send an email using a SendGrid template.
        """
        try:
            from sendgrid.helpers.mail import Mail
            
            from_addr = from_email or self.default_from_email
            
            # Create message with template
            message = Mail(
                from_email=from_addr,
                to_emails=to,
            )
            
            # Set template ID
            message.template_id = template_id
            
            # Add dynamic template data
            message.dynamic_template_data = template_data
            
            # Add CC, BCC, reply-to (similar to send_email)
            if cc or bcc:
                from sendgrid.helpers.mail import Personalization, Cc, Bcc, To
                personalization = Personalization()
                for recipient in to:
                    personalization.add_to(To(recipient))
                if cc:
                    for cc_email in cc:
                        personalization.add_cc(Cc(cc_email))
                if bcc:
                    for bcc_email in bcc:
                        personalization.add_bcc(Bcc(bcc_email))
                message.add_personalization(personalization)
            
            if reply_to:
                from sendgrid.helpers.mail import ReplyTo
                message.reply_to = ReplyTo(reply_to[0])
            
            # Add metadata
            if metadata:
                from sendgrid.helpers.mail import CustomArg
                for key, value in metadata.items():
                    message.add_custom_arg(CustomArg(key, str(value)))
            
            # Send email
            response = self.client.send(message)
            
            message_id = response.headers.get('X-Message-Id', 'unknown')
            
            logger.info(f"Template email sent via SendGrid to {to}: template {template_id}")
            
            return {
                'message_id': message_id,
                'status': 'sent' if response.status_code in [200, 202] else 'failed',
                'provider_response': {
                    'status_code': response.status_code,
                    'body': response.body,
                    'headers': dict(response.headers),
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to send template email via SendGrid: {e}")
            if "template" in str(e).lower():
                raise TemplateNotFoundError(f"Template not found: {template_id}")
            raise EmailSendError(f"Failed to send template email: {str(e)}")

    def send_bulk_email(
        self,
        recipients: List[Dict[str, Any]],
        subject: str,
        text_body: Optional[str] = None,
        html_body: Optional[str] = None,
        from_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send bulk emails with personalization using SendGrid.
        """
        try:
            from sendgrid.helpers.mail import Mail, Personalization, To, Content
            
            from_addr = from_email or self.default_from_email
            
            # Create base message
            message = Mail(from_email=from_addr)
            message.subject = subject
            
            if text_body:
                message.add_content(Content("text/plain", text_body))
            if html_body:
                message.add_content(Content("text/html", html_body))
            
            # Add personalizations for each recipient
            # Note: SendGrid uses -key- format for substitutions, while SMTP uses $key
            # This is a provider-specific format. See README.md for details.
            for recipient in recipients:
                personalization = Personalization()
                personalization.add_to(To(recipient['to']))
                
                # Add substitutions if provided
                # SendGrid uses -key- format for substitutions
                if 'substitutions' in recipient:
                    for key, value in recipient['substitutions'].items():
                        # Use SendGrid's substitution format: -key-
                        personalization.add_substitution(f'-{key}-', str(value))
                
                message.add_personalization(personalization)
            
            # Add metadata
            if metadata:
                from sendgrid.helpers.mail import CustomArg
                for key, value in metadata.items():
                    message.add_custom_arg(CustomArg(key, str(value)))
            
            # Send email
            response = self.client.send(message)
            
            total_sent = len(recipients) if response.status_code in [200, 202] else 0
            total_failed = len(recipients) - total_sent
            
            logger.info(f"Bulk email sent via SendGrid: {total_sent} sent, {total_failed} failed")
            
            return {
                'total_sent': total_sent,
                'total_failed': total_failed,
                'failed_recipients': [],
            }
            
        except Exception as e:
            logger.error(f"Failed to send bulk email via SendGrid: {e}")
            return {
                'total_sent': 0,
                'total_failed': len(recipients),
                'failed_recipients': [{'email': r['to'], 'error': str(e)} for r in recipients],
            }

    def verify_email(self, email: str) -> Dict[str, Any]:
        """
        Verify an email address using SendGrid's validation API.
        """
        try:
            # Note: This requires SendGrid's Email Validation API
            # which is a separate paid service
            logger.warning("SendGrid email verification requires Email Validation API")
            
            # Basic validation as fallback
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            is_valid = bool(re.match(email_pattern, email))
            
            return {
                'is_valid': is_valid,
                'reason': 'format_check',
                'provider_response': {
                    'note': 'Basic validation only. Enable SendGrid Email Validation API for full verification'
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to verify email: {e}")
            return {
                'is_valid': False,
                'reason': 'error',
                'provider_response': {'error': str(e)}
            }

    def get_send_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get email sending statistics from SendGrid.
        """
        try:
            # Build query parameters
            params = {}
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            
            # Get stats from SendGrid API
            response = self.client.client.stats.get(query_params=params)
            
            if response.status_code == 200:
                stats_data = json.loads(response.body)
                
                # Aggregate statistics
                total_stats = {
                    'sent': 0,
                    'delivered': 0,
                    'bounced': 0,
                    'complained': 0,
                    'opened': 0,
                    'clicked': 0,
                }
                
                for stat in stats_data:
                    metrics = stat.get('metrics', {})
                    total_stats['sent'] += metrics.get('requests', 0)
                    total_stats['delivered'] += metrics.get('delivered', 0)
                    total_stats['bounced'] += metrics.get('bounces', 0)
                    total_stats['complained'] += metrics.get('spam_reports', 0)
                    total_stats['opened'] += metrics.get('unique_opens', 0)
                    total_stats['clicked'] += metrics.get('unique_clicks', 0)
                
                return total_stats
            else:
                logger.error(f"Failed to get statistics: {response.status_code}")
                return {
                    'sent': 0,
                    'delivered': 0,
                    'bounced': 0,
                    'complained': 0,
                    'opened': 0,
                    'clicked': 0,
                }
                
        except Exception as e:
            logger.error(f"Failed to get statistics from SendGrid: {e}")
            return {
                'sent': 0,
                'delivered': 0,
                'bounced': 0,
                'complained': 0,
                'opened': 0,
                'clicked': 0,
            }

    def add_to_suppression_list(
        self,
        email: str,
        reason: str = 'manual',
    ) -> Dict[str, Any]:
        """
        Add an email to SendGrid's suppression list.
        """
        try:
            # Map reason to SendGrid suppression group
            # 'bounce', 'complaint', 'manual' -> blocks, bounces, spam_reports
            endpoint_map = {
                'bounce': 'bounces',
                'complaint': 'spam_reports',
                'manual': 'blocks',
            }
            
            endpoint = endpoint_map.get(reason, 'blocks')
            
            # Add to suppression list
            data = {
                'emails': [email]
            }
            
            response = self.client.client.suppression._(endpoint).post(request_body=data)
            
            logger.info(f"Added {email} to SendGrid suppression list ({endpoint})")
            
            return {
                'email': email,
                'status': 'added' if response.status_code in [200, 201] else 'failed',
                'reason': reason,
            }
            
        except Exception as e:
            logger.error(f"Failed to add to suppression list: {e}")
            return {
                'email': email,
                'status': 'failed',
                'reason': reason,
                'error': str(e)
            }

    def remove_from_suppression_list(self, email: str) -> Dict[str, Any]:
        """
        Remove an email from SendGrid's suppression lists.
        """
        try:
            # Try to remove from all suppression lists
            suppression_lists = ['blocks', 'bounces', 'spam_reports', 'invalid_emails']
            removed_from = []
            
            for list_name in suppression_lists:
                try:
                    response = self.client.client.suppression._(list_name)._(email).delete()
                    if response.status_code in [200, 204]:
                        removed_from.append(list_name)
                except Exception:
                    # Ignore errors for individual list operations
                    pass
            
            logger.info(f"Removed {email} from SendGrid suppression lists: {removed_from}")
            
            return {
                'email': email,
                'status': 'removed' if removed_from else 'not_found',
                'removed_from': removed_from,
            }
            
        except Exception as e:
            logger.error(f"Failed to remove from suppression list: {e}")
            return {
                'email': email,
                'status': 'failed',
                'error': str(e)
            }

    def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Validate webhook signature from SendGrid.
        """
        try:
            from sendgrid.helpers.eventwebhook import EventWebhook, EventWebhookHeader
            
            # Get webhook verification key from settings
            verification_key = getattr(settings, 'SENDGRID_WEBHOOK_VERIFICATION_KEY', None)
            if not verification_key:
                logger.warning("SENDGRID_WEBHOOK_VERIFICATION_KEY not set in settings")
                return False
            
            event_webhook = EventWebhook()
            ec_public_key = event_webhook.convert_public_key_to_ecdsa(verification_key)
            
            # Verify signature
            is_valid = event_webhook.verify_signature(
                payload.decode('utf-8'),
                signature,
                timestamp,
                ec_public_key
            )
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Failed to validate webhook signature: {e}")
            return False
