from django.db import models
from django.conf import settings
import uuid

class UserIdentity(models.Model):
    """
    Maps an external Identity Provider user to an internal Django User.
    This is the core of the 'Abstraction Layer'.
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
        unique_together = ('provider', 'provider_user_id')
        indexes = [
            models.Index(fields=['provider', 'provider_user_id']),
        ]

    def __str__(self):
        return f"{self.provider}:{self.provider_user_id} -> {self.user}"
