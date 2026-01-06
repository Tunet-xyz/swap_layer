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

    def to_dto(self) -> PydanticIdentity:
        return PydanticIdentity(
            id=self.id,
            user_id=str(self.user.pk),
            provider=self.provider,
            provider_user_id=self.provider_user_id,
            email=self.email,
            data=self.data,
            created_at=self.created_at,
            updated_at=self.updated_at
        )
