from typing import Dict, Any
from django.conf import settings
from django.contrib.auth import get_user_model
from ..models import IdentityVerificationSession
from ..schemas import VerificationSessionCreate
from ..factory import get_identity_verification_provider
import logging

logger = logging.getLogger(__name__)


class IdentityOperations:
    """
    Main operations class for Identity Service.
    Handles business logic, database operations, and webhook processing.
    Uses the factory pattern to get the configured provider.
    """
    
    def __init__(self, provider=None):
        """
        Initialize IdentityOperations.
        
        Args:
            provider: Optional provider instance for dependency injection (useful for testing)
        """
        self.provider = provider or get_identity_verification_provider()
        # Extract provider name from settings for backward compatibility
        self.provider_name = getattr(settings, 'IDENTITY_VERIFICATION_PROVIDER', 'stripe')

    def create_session(self, user, data: VerificationSessionCreate) -> IdentityVerificationSession:
        """
        Creates a verification session with the provider and saves it to the DB.
        """
        
        # 1. Call Provider
        # Auto-populate email if not provided but available on user
        email = data.email
        if not email and hasattr(user, 'email') and user.email:
            email = user.email

        provider_data = self.provider.create_verification_session(
            user=user,
            verification_type=data.verification_type,
            options={
                'return_url': data.return_url,
                'metadata': data.metadata,
                'email': email
            }
        )
        
        # 2. Save to DB
        session = IdentityVerificationSession.objects.create(
            user=user,
            provider=self.provider_name,
            provider_session_id=provider_data['provider_session_id'],
            status=provider_data['status'],
            verification_type=provider_data['type'],
            client_secret=provider_data.get('client_secret', ''),
            metadata=data.metadata
        )
        
        return session

    def get_session(self, session_id: int) -> IdentityVerificationSession:
        return IdentityVerificationSession.objects.get(id=session_id)

    def get_session_by_provider_id(self, provider_session_id: str) -> IdentityVerificationSession:
        return IdentityVerificationSession.objects.get(provider_session_id=provider_session_id)

    def cancel_session(self, session_id: int) -> IdentityVerificationSession:
        session = self.get_session(session_id)
        provider_data = self.provider.cancel_verification_session(session.provider_session_id)
        session.status = provider_data['status']
        session.save()
        return session

    def redact_session(self, session_id: int) -> IdentityVerificationSession:
        session = self.get_session(session_id)
        provider_data = self.provider.redact_verification_session(session.provider_session_id)
        session.status = provider_data['status']
        # Clear PII from our DB as well
        session.verified_first_name = ''
        session.verified_last_name = ''
        session.verified_dob = None
        session.verified_address_line1 = ''
        session.verified_address_city = ''
        session.verified_address_postal_code = ''
        session.verified_address_country = ''
        session.save()
        return session

    def get_insights(self, session_id: int) -> Dict[str, Any]:
        session = self.get_session(session_id)
        return self.provider.get_verification_insights(session.provider_session_id)

    def list_sessions(self, user, limit: int = 10):
        # We prefer listing from our DB as it's faster and allows filtering by user easily
        return IdentityVerificationSession.objects.filter(user=user).order_by('-created_at')[:limit]

    def sync_session_status(self, session: IdentityVerificationSession) -> IdentityVerificationSession:
        """
        Fetches latest status from provider and updates DB.
        """
        provider_data = self.provider.get_verification_session(session.provider_session_id)
        
        session.status = provider_data['status']
        
        # Update verification report ID
        if provider_data.get('last_verification_report'):
            # It might be an ID or an object depending on expansion
            report = provider_data['last_verification_report']
            if isinstance(report, str):
                session.verification_report_id = report
            elif hasattr(report, 'id'):
                session.verification_report_id = report.id
            elif isinstance(report, dict):
                session.verification_report_id = report.get('id')

        # Update verified outputs if available
        outputs = provider_data.get('verified_outputs')
        if outputs:
            session.verified_first_name = outputs.get('first_name', '')
            session.verified_last_name = outputs.get('last_name', '')
            session.verified_address_city = outputs.get('address', {}).get('city', '')
            session.verified_address_country = outputs.get('address', {}).get('country', '')
            session.verified_address_line1 = outputs.get('address', {}).get('line1', '')
            session.verified_address_postal_code = outputs.get('address', {}).get('postal_code', '')
            
            if outputs.get('dob'):
                try:
                    # Simple parsing, might need adjustment based on provider format
                    dob_dict = outputs.get('dob')
                    from datetime import date
                    session.verified_dob = date(int(dob_dict['year']), int(dob_dict['month']), int(dob_dict['day']))
                except Exception:
                    pass
                
        session.save()
        return session

    def process_webhook(self, payload: bytes, signature: str):
        """
        Process a webhook from the provider.
        """
        try:
            event = self.provider.handle_webhook(payload, signature)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise

        # Normalize event data (Provider specific -> Generic)
        # For Stripe, event is a dict-like object
        event_type = event.get('type')
        data = event.get('data', {}).get('object', {})
        
        if not event_type or not data:
            return

        # Map Stripe events to our logic
        if event_type == 'identity.verification_session.verified':
            self._handle_verified(data)
        elif event_type == 'identity.verification_session.requires_input':
            self._handle_requires_input(data)
        elif event_type == 'identity.verification_session.canceled':
            self._handle_canceled(data)
        elif event_type == 'identity.verification_session.processing':
            self._handle_processing(data)
        elif event_type == 'identity.verification_session.redacted':
            self._handle_redacted(data)

    def _handle_verified(self, data):
        provider_session_id = data.get('id')
        try:
            session = self.get_session_by_provider_id(provider_session_id)
            self.sync_session_status(session)
            
            # Send Email
            self._send_email(
                session.user,
                "Identity Verification Successful",
                f"Hi {session.user.username},\n\nYour identity verification has been successfully completed!"
            )
            
            logger.info(f"Verification verified for user {session.user.id}")
        except IdentityVerificationSession.DoesNotExist:
            logger.warning(f"Session {provider_session_id} not found during webhook processing")

    def _handle_requires_input(self, data):
        provider_session_id = data.get('id')
        try:
            session = self.get_session_by_provider_id(provider_session_id)
            self.sync_session_status(session)
            
            self._send_email(
                session.user,
                "Identity Verification - Additional Information Required",
                f"Hi {session.user.username},\n\nWe need some additional information to complete your identity verification."
            )
        except IdentityVerificationSession.DoesNotExist:
            pass

    def _handle_canceled(self, data):
        provider_session_id = data.get('id')
        try:
            session = self.get_session_by_provider_id(provider_session_id)
            self.sync_session_status(session)
        except IdentityVerificationSession.DoesNotExist:
            pass

    def _handle_processing(self, data):
        provider_session_id = data.get('id')
        try:
            session = self.get_session_by_provider_id(provider_session_id)
            self.sync_session_status(session)
        except IdentityVerificationSession.DoesNotExist:
            pass

    def _handle_redacted(self, data):
        provider_session_id = data.get('id')
        try:
            session = self.get_session_by_provider_id(provider_session_id)
            self.sync_session_status(session)
            # Also clear local PII
            session.verified_first_name = ''
            session.verified_last_name = ''
            session.verified_dob = None
            session.verified_address_line1 = ''
            session.verified_address_city = ''
            session.verified_address_postal_code = ''
            session.verified_address_country = ''
            session.save()
            logger.info(f"Verification redacted for user {session.user.id}")
        except IdentityVerificationSession.DoesNotExist:
            pass

    def _send_email(self, user, subject, message):
        try:
            from email.factory import get_email_provider
            
            provider = get_email_provider()
            provider.send_email(
                to=[user.email],
                subject=subject,
                text_body=message,
            )
        except Exception as e:
            logger.error(f"Error sending email to {user.email}: {e}")
