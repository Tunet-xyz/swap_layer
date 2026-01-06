"""
Django repository for persisting User Identity mappings.
"""

from typing import Optional, Any
from django.apps import apps
from django.conf import settings
from .models import UserIdentity


class PlatformRepository:
    """
    Repository for persisting User Identity mappings to Django models.
    Requires SWAP_LAYER_IDENTITY_MODEL setting pointing to your UserIdentity model.
    """
    
    def __init__(self):
        model_path = getattr(settings, 'SWAP_LAYER_IDENTITY_MODEL', None)
        if not model_path:
            raise ValueError(
                "SWAP_LAYER_IDENTITY_MODEL must be set to use Django persistence. "
                "Example: SWAP_LAYER_IDENTITY_MODEL = 'myapp.UserIdentity'"
            )
        self.model = apps.get_model(model_path)

    def save(self, identity: UserIdentity) -> Any:
        """Save or update a user identity mapping."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user_instance = User.objects.get(pk=identity.user_id)
        except User.DoesNotExist:
            raise ValueError(f"User {identity.user_id} not found")

        try:
            obj = self.model.objects.get(
                provider=identity.provider, 
                provider_user_id=identity.provider_user_id
            )
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

    def get(self, provider: str, provider_user_id: str) -> Optional[UserIdentity]:
        """Get a user identity by provider and provider user ID."""
        try:
            obj = self.model.objects.get(provider=provider, provider_user_id=provider_user_id)
            if hasattr(obj, 'to_dto'):
                return obj.to_dto()
            return None
        except self.model.DoesNotExist:
            return None

    def get_by_user(self, user_id: str) -> Optional[UserIdentity]:
        """Get a user identity by user ID (returns first match)."""
        try:
            obj = self.model.objects.filter(user__pk=user_id).first()
            if obj and hasattr(obj, 'to_dto'):
                return obj.to_dto()
            return None
        except self.model.DoesNotExist:
            return None
