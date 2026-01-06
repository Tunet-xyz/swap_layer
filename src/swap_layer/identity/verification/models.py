from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Union, Literal
from datetime import datetime, date
import uuid

class IdentityVerificationSession(BaseModel):
    """
    Stores identity verification session data.
    """
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    # Generic user reference
    user_id: Union[str, int]
    
    provider: str = 'stripe' 
    provider_session_id: str = Field(description="Session ID from the identity provider")
    
    status: str = Field(default='requires_input')
    verification_type: str = Field(default='document')
    
    client_secret: Optional[str] = Field(default=None, description="Client secret for frontend integration")
    verification_report_id: Optional[str] = Field(default=None, description="ID of the verification report")
    
    verified_at: Optional[datetime] = Field(default=None, description="When the verification was completed")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Verified outputs
    verified_first_name: Optional[str] = None
    verified_last_name: Optional[str] = None
    verified_dob: Optional[date] = None
    verified_address_line1: Optional[str] = None
    verified_address_city: Optional[str] = None
    verified_address_postal_code: Optional[str] = None
    verified_address_country: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    model_config = {
        "json_encoders": {
            uuid.UUID: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
    }

    def __str__(self):
        return f"{self.user_id} - {self.provider} - {self.status}"
