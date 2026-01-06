from django.db import models
from django.conf import settings
from typing import Optional
from ..models import IdentityVerificationSession as PydanticSession

class AbstractIdentityVerificationSession(models.Model):
    """
    An abstract Django model that allows easy persistence of Swap Layer verification sessions.
    Users can inherit from this to add their own fields or relations.
    """
    # We map Pydantic fields to Django ORM fields here
    provider_session_id = models.CharField(
        max_length=255, 
        unique=True, 
        db_index=True,
        help_text="Session ID from the identity provider"
    )
    # We assume standard user relation, but allow overriding if needed in concrete model
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='identity_verifications'
    )
    
    status = models.CharField(max_length=50, db_index=True)
    verification_type = models.CharField(max_length=50)
    provider = models.CharField(max_length=50)
    
    client_secret = models.CharField(max_length=255, blank=True, null=True)
    verification_report_id = models.CharField(max_length=255, blank=True, null=True)
    
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Store the full metadata blob
    metadata = models.JSONField(default=dict, blank=True)

    # Simplified Verified Data 
    verified_first_name = models.CharField(max_length=255, blank=True)
    verified_last_name = models.CharField(max_length=255, blank=True)
    
    class Meta:
        abstract = True

    @classmethod
    def from_dto(cls, dto: PydanticSession, user_instance) -> 'AbstractIdentityVerificationSession':
        """
        Helper to create a Django model instance from the Pydantic DTO.
        """
        return cls(
            user=user_instance,
            provider_session_id=dto.provider_session_id,
            status=dto.status,
            verification_type=dto.verification_type,
            provider=dto.provider,
            client_secret=dto.client_secret,
            metadata=dto.metadata,
            verification_report_id=dto.verification_report_id,
            verified_at=dto.verified_at,
            verified_first_name=dto.verified_first_name,
            verified_last_name=dto.verified_last_name,
            # Add other verified fields as needed
        )

from ..repository import VerificationRepository
from ..services import VerificationService
from django.apps import apps
from django.conf import settings as django_settings
from typing import Optional, Any
from ..schemas import VerificationSessionCreate

class DjangoVerificationRepository(VerificationRepository):
    """
    Implementation of the repository that saves to a Django Model.
    Requires SWAP_LAYER_VERIFICATION_MODEL setting.
    """
    
    def __init__(self):
        model_path = getattr(django_settings, 'SWAP_LAYER_VERIFICATION_MODEL', None)
        if not model_path:
            raise ValueError("SWAP_LAYER_VERIFICATION_MODEL must be set to use Django persistence.")
        self.model = apps.get_model(model_path)
        
    def save(self, session: PydanticSession) -> Any:
        # We need the User instance to save the model
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user_instance = User.objects.get(pk=session.user_id)
        except User.DoesNotExist:
            # Fallback or strict error? 
            # For now, let's assume valid user_id
            raise ValueError(f"User {session.user_id} not found")
            
        # Check if exists to update
        try:
            obj = self.model.objects.get(provider_session_id=session.provider_session_id)
            # Update fields
            obj.status = session.status
            obj.metadata = session.metadata
            obj.verification_report_id = session.verification_report_id
            obj.verified_at = session.verified_at
            if session.verified_first_name: obj.verified_first_name = session.verified_first_name
            if session.verified_last_name: obj.verified_last_name = session.verified_last_name
            # ... and so on
            obj.save()
            return obj
        except self.model.DoesNotExist:
            # Create new using the helper on the abstract base (if available) or manual
            if hasattr(self.model, 'from_dto'):
                obj = self.model.from_dto(session, user_instance)
                obj.save()
                return obj
            else:
                 # Fallback manual creation if they didn't inherit our Abstract Base
                 # This is risky but standard django
                 obj = self.model.objects.create(
                     user=user_instance,
                     provider_session_id=session.provider_session_id,
                     status=session.status,
                     verification_type=session.verification_type,
                     provider=session.provider,
                     metadata=session.metadata
                 )
                 return obj

    def get(self, session_id: str) -> Optional[PydanticSession]:
        try:
            obj = self.model.objects.get(pk=session_id)
            if hasattr(obj, 'to_dto'):
                return obj.to_dto()
            return None # Or manual mapping
        except self.model.DoesNotExist:
            return None

    def get_by_provider_id(self, provider_session_id: str) -> Optional[PydanticSession]:
        try:
            obj = self.model.objects.get(provider_session_id=provider_session_id)
            if hasattr(obj, 'to_dto'):
                return obj.to_dto()
            return None
        except self.model.DoesNotExist:
            return None

class DjangoVerificationService(VerificationService):
    """
    The High-Level Service for Django applications.
    Wraps the Core Operations and the Django Repository.
    """
    def __init__(self):
        super().__init__()
        self.repository = DjangoVerificationRepository()

    def create_session(self, user_id: str, data: VerificationSessionCreate, user_email: Optional[str] = None) -> Any:
        # 1. Call Core Pydantic Logic
        session_dto = self.ops.create_session(user_id, data, user_email)
        
        # 2. Persist to Django Model
        saved_instance = self.repository.save(session_dto)
        
        # 3. Return the Django Model Instance (Best DX for Django users)
        return saved_instance

    def cancel_session(self, provider_session_id: str) -> Dict[str, Any]:
        # Cancel at provider
        result = self.ops.cancel_session(provider_session_id)
        # Update local model if exists
        try:
             # We fetch via repository to ensure we get the model
             # But repository.get_by_provider_id returns DTO, we want to update the model.
             # So we use the model directly here or add update method to repository.
             # For simplicity and performance in Django context:
             obj = self.repository.model.objects.get(provider_session_id=provider_session_id)
             if 'status' in result:
                 obj.status = result['status']
                 obj.save()
        except self.repository.model.DoesNotExist:
            pass
        return result

    def get_insights(self, provider_session_id: str) -> Dict[str, Any]:
        return self.ops.get_insights(provider_session_id)


