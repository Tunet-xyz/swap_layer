from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class EmailProviderAdapter(ABC):
    """
    Abstract base class for Email Providers (SMTP, SendGrid, Mailgun, AWS SES, etc.)
    This ensures we can switch providers without rewriting the application logic.
    """

    @abstractmethod
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
        Send an email.
        
        Args:
            to: List of recipient email addresses
            subject: Email subject line
            text_body: Plain text email body (optional if html_body provided)
            html_body: HTML email body (optional if text_body provided)
            from_email: Sender email address (uses default if not provided)
            cc: List of CC email addresses
            bcc: List of BCC email addresses
            reply_to: List of reply-to email addresses
            attachments: List of attachment dicts with 'filename', 'content', 'mimetype'
            headers: Custom email headers
            metadata: Provider-specific metadata
        
        Returns:
            Dict with keys: message_id, status, provider_response
        
        Raises:
            EmailSendError: If email sending fails
        """
        pass

    @abstractmethod
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
        Send an email using a template.
        
        Args:
            to: List of recipient email addresses
            template_id: Template identifier in the provider
            template_data: Data to populate the template
            from_email: Sender email address (uses default if not provided)
            cc: List of CC email addresses
            bcc: List of BCC email addresses
            reply_to: List of reply-to email addresses
            metadata: Provider-specific metadata
        
        Returns:
            Dict with keys: message_id, status, provider_response
        
        Raises:
            EmailSendError: If email sending fails
            TemplateNotFoundError: If template doesn't exist
        """
        pass

    @abstractmethod
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
        Send bulk emails with personalization.
        
        Args:
            recipients: List of dicts with 'to' and optional 'substitutions'
            subject: Email subject line (can include variables)
            text_body: Plain text email body (can include variables)
            html_body: HTML email body (can include variables)
            from_email: Sender email address
            metadata: Provider-specific metadata
        
        Returns:
            Dict with keys: total_sent, total_failed, failed_recipients
        """
        pass

    @abstractmethod
    def verify_email(self, email: str) -> Dict[str, Any]:
        """
        Verify an email address (if supported by provider).
        
        Args:
            email: Email address to verify
        
        Returns:
            Dict with keys: is_valid, reason, provider_response
        """
        pass

    @abstractmethod
    def get_send_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get email sending statistics.
        
        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
        
        Returns:
            Dict with keys: sent, delivered, bounced, complained, opened, clicked
        """
        pass

    @abstractmethod
    def add_to_suppression_list(
        self,
        email: str,
        reason: str = 'manual',
    ) -> Dict[str, Any]:
        """
        Add an email to the suppression list (bounce/complaint list).
        
        Args:
            email: Email address to suppress
            reason: Reason for suppression (bounce, complaint, manual)
        
        Returns:
            Dict with keys: email, status, reason
        """
        pass

    @abstractmethod
    def remove_from_suppression_list(self, email: str) -> Dict[str, Any]:
        """
        Remove an email from the suppression list.
        
        Args:
            email: Email address to remove from suppression
        
        Returns:
            Dict with keys: email, status
        """
        pass

    @abstractmethod
    def validate_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: Optional[str] = None,
    ) -> bool:
        """
        Validate webhook signature from the email provider.
        
        Args:
            payload: Raw request body
            signature: Signature from webhook headers
            timestamp: Timestamp from webhook headers (if applicable)
        
        Returns:
            True if signature is valid, False otherwise
        """
        pass


class EmailSendError(Exception):
    """Raised when email sending fails."""
    pass


class TemplateNotFoundError(Exception):
    """Raised when a template is not found."""
    pass
