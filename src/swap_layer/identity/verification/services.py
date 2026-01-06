"""
Django service layer for identity verification operations.
"""

from typing import Any, Dict, Optional
from .schemas import VerificationSessionCreate
from .operations.core import IdentityOperations
from .repository import VerificationRepository


class VerificationService:
    """
    High-level Django service for identity verification operations.
    Handles verification sessions and persists them to Django models.
    """
    
    def __init__(self, operations: IdentityOperations = None):
        self.ops = operations or IdentityOperations()
        self.repository = VerificationRepository()

    def create_session(self, user_id: str, data: VerificationSessionCreate, user_email: Optional[str] = None) -> Any:
        """
        Create a verification session and persist to database.
        
        Args:
            user_id: Django user ID
            data: Verification session creation parameters
            user_email: Optional user email for verification
            
        Returns:
            Saved Django model instance
        """
        # 1. Call Core Pydantic Logic
        session_dto = self.ops.create_session(user_id, data, user_email)
        
        # 2. Persist to Django Model
        saved_instance = self.repository.save(session_dto)
        
        # 3. Return the Django Model Instance (Best DX for Django users)
        return saved_instance

    def cancel_session(self, provider_session_id: str) -> Dict[str, Any]:
        """
        Cancel a verification session at the provider and update local database.
        
        Args:
            provider_session_id: Provider's session ID
            
        Returns:
            Dict with cancellation result
        """
        # Cancel at provider
        result = self.ops.cancel_session(provider_session_id)
        # Update local model if exists
        try:
            obj = self.repository.model.objects.get(provider_session_id=provider_session_id)
            if 'status' in result:
                obj.status = result['status']
                obj.save()
        except self.repository.model.DoesNotExist:
            pass
        return result

    def get_insights(self, provider_session_id: str) -> Dict[str, Any]:
        """
        Get verification insights from the provider.
        
        Args:
            provider_session_id: Provider's session ID
            
        Returns:
            Dict with verification insights
        """
        return self.ops.get_insights(provider_session_id)
