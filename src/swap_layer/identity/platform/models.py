from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, Union
from datetime import datetime
import uuid

class UserIdentity(BaseModel):
    """
    Maps an external Identity Provider user to an internal User.
    This is the core of the 'Abstraction Layer'.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    # Removing direct ForeignKey dependency. The consuming app should handle the relation.
    # We accept int or str for user_id to be agnostic
    user_id: Union[str, int]
    provider: str # e.g. 'workos', 'auth0', 'supabase'
    provider_user_id: str
    
    # Optional: Store extra data from the provider
    email: Optional[EmailStr] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    model_config = {
        "json_encoders": {
            uuid.UUID: str,
            datetime: lambda v: v.isoformat(),
        }
    }

    def __str__(self):
        return f"{self.provider}:{self.provider_user_id} -> {self.user_id}"
