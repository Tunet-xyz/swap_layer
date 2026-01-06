"""
Django repository for persisting identity verification sessions.
"""

from typing import Optional, Any
from django.apps import apps
from django.conf import settings
from .models import IdentityVerificationSession


class VerificationRepository:
    """
    Repository for persisting verification sessions to Django models.
    Requires SWAP_LAYER_VERIFICATION_MODEL setting pointing to your verification model.
    """
    
    def __init__(self):
        model_path = getattr(settings, 'SWAP_LAYER_VERIFICATION_MODEL', None)
        if not model_path:
            raise ValueError(
                "SWAP_LAYER_VERIFICATION_MODEL must be set to use Django persistence. "
                "Example: SWAP_LAYER_VERIFICATION_MODEL = 'myapp.IdentityVerification'"
            )
        self.model = apps.get_model(model_path)
        
    def save(self, session: IdentityVerificationSession) -> Any:
        """Save or update a verification session."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user_instance = User.objects.get(pk=session.user_id)
        except User.DoesNotExist:
            raise ValueError(f"User {session.user_id} not found")
            
        # Check if exists to update
        try:
            obj = self.model.objects.get(provider_session_id=session.provider_session_id)
            # Update fields
            obj.status = session.status
            obj.metadata = session.metadata
            obj.verification_report_id = session.verification_report_id
            obj.verified_at = session.verified_at
            if session.verified_first_name: 
                obj.verified_first_name = session.verified_first_name
            if session.verified_last_name: 
                obj.verified_last_name = session.verified_last_name
            obj.save()
            return obj
        except self.model.DoesNotExist:
            # Create new using the helper on the abstract base (if available)
            if hasattr(self.model, 'from_dto'):
                obj = self.model.from_dto(session, user_instance)
                obj.save()
                return obj
            else:
                # Fallback manual creation
                obj = self.model.objects.create(
                    user=user_instance,
                    provider_session_id=session.provider_session_id,
                    status=session.status,
                    verification_type=session.verification_type,
                    provider=session.provider,
                    metadata=session.metadata
                )
                return obj

    def get(self, session_id: str) -> Optional[IdentityVerificationSession]:
        """Get a verification session by internal ID."""
        try:
            obj = self.model.objects.get(pk=session_id)
            if hasattr(obj, 'to_dto'):
                return obj.to_dto()
            return None
        except self.model.DoesNotExist:
            return None

    def get_by_provider_id(self, provider_session_id: str) -> Optional[IdentityVerificationSession]:
        """Get a verification session by provider session ID."""
        try:
            obj = self.model.objects.get(provider_session_id=provider_session_id)
            if hasattr(obj, 'to_dto'):
                return obj.to_dto()
            return None
        except self.model.DoesNotExist:
            return None
