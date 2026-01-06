from django.db import models
from django.conf import settings
from typing import Optional
from ..models import UserIdentity as PydanticIdentity
import uuid

class AbstractUserIdentity(models.Model):
    """
    An abstract Django model for User Identity mapping.
    Maps an external Identity Provider user to an internal Django User.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='identities')
    provider = models.CharField(max_length=50) # e.g. 'workos', 'auth0', 'supabase'
    provider_user_id = models.CharField(max_length=255)
    
    # Optional: Store extra data from the provider
    email = models.EmailField(null=True, blank=True)
    data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        unique_together = ('provider', 'provider_user_id')
        indexes = [
            models.Index(fields=['provider', 'provider_user_id']),
        ]

    def __str__(self):
        return f"{self.provider}:{self.provider_user_id} -> {self.user}"

    @classmethod
    def from_dto(cls, dto: PydanticIdentity, user_instance) -> 'AbstractUserIdentity':
        return cls(
            id=dto.id,
            user=user_instance,
            provider=dto.provider,
            provider_user_id=dto.provider_user_id,
            email=dto.email,
            data=dto.data
        )

from ..repository import PlatformRepository
from ..services import AuthenticationService
from django.apps import apps
from django.conf import settings as django_settings
from typing import Any, Dict, Optional

class DjangoPlatformRepository(PlatformRepository):
    """
    Implementation of the repository that saves to a Django Model.
    Requires SWAP_LAYER_IDENTITY_MODEL setting.
    """
    def __init__(self):
        model_path = getattr(django_settings, 'SWAP_LAYER_IDENTITY_MODEL', None)
        if not model_path:
            raise ValueError("SWAP_LAYER_IDENTITY_MODEL must be set to use Django persistence.")
        self.model = apps.get_model(model_path)

    def save(self, identity: PydanticIdentity) -> Any:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user_instance = User.objects.get(pk=identity.user_id)
        except User.DoesNotExist:
             raise ValueError(f"User {identity.user_id} not found")

        try:
            obj = self.model.objects.get(provider=identity.provider, provider_user_id=identity.provider_user_id)
            obj.email = identity.email
            obj.data = identity.data
            obj.save()
            return obj
        except self.model.DoesNotExist:
            if hasattr(self.model, 'from_dto'):
                obj = self.model.from_dto(identity, user_instance)
                obj.save()
                return obj
            else:
                 obj = self.model.objects.create(
                     user=user_instance,
                     provider=identity.provider,
                     provider_user_id=identity.provider_user_id,
                     email=identity.email,
                     data=identity.data
                 )
                 return obj

    def get(self, provider: str, provider_user_id: str) -> Optional[PydanticIdentity]:
        try:
            obj = self.model.objects.get(provider=provider, provider_user_id=provider_user_id)
            if hasattr(obj, 'to_dto'):
                return obj.to_dto()
            return None
        except self.model.DoesNotExist:
            return None

    def get_by_user(self, user_id: str) -> Optional[PydanticIdentity]:
        try:
             # Assuming one identity per user for simplicity or getting the first
            obj = self.model.objects.filter(user__pk=user_id).first()
            if obj and hasattr(obj, 'to_dto'):
                return obj.to_dto()
            return None
        except self.model.DoesNotExist:
            return None

class DjangoAuthenticationService(AuthenticationService):
    """
    Django Service that saves the identity link on login.
    """
    def __init__(self):
        super().__init__()
        self.repository = DjangoPlatformRepository()

    def get_login_url(self, request: Any, redirect_uri: str, state: Optional[str] = None) -> str:
        return self.ops.get_authorization_url(request, redirect_uri, state)

    def complete_login(self, request: Any, code: str) -> Any:
        # 1. Exchange code
        user_data = self.ops.exchange_code(request, code)
        
        # 2. In a real Django app, this is where we would:
        #    a) Find user by email OR
        #    b) Find identity link -> get user
        #    c) Create user if not exists
        #    d) Login via django.contrib.auth.login
        
        # However, the library user (the dev) handles the User model creation logic usually.
        # But for this Service to be "Batteries Included", we might need to assume behavior 
        # or just return the data and let the view handle it.
        # BUT, the Repository saves "UserIdentity" which requires a USER ID.
        # So we can't save unless we have a user.
        
        # Strategy: This service returns the raw data AND the Identity DTO construction helper.
        # It's up to the view to call repository.save(dto) after they determine the User.
        
        # WAIT, if "Service Strategy" implies full handling, then we need a way to resolving users.
        # For now, let's keep it simple: Return the data.
        # But if we want to "Finish the Job", we should provide a helper to save the link easily.
        
        return user_data

    def get_logout_url(self, request: Any, return_to: str) -> str:
        return self.ops.get_logout_url(request, return_to)

    def link_identity(self, user_id: str, provider_data: Dict[str, Any]):
        """
        Explicit method to link an authenticated provider user to a local user.
        """
        dto = self.ops.create_identity_dto(user_id, provider_data)
        return self.repository.save(dto)

