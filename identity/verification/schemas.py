from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, Dict, Any

class VerificationSessionCreate(BaseModel):
    verification_type: str = Field(default='document', pattern='^(document|id_number)$')
    return_url: Optional[str] = None
    email: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class VerificationSessionRead(BaseModel):
    id: int
    provider: str
    provider_session_id: str
    status: str
    verification_type: str
    client_secret: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    
    # Verified Data
    verified_first_name: Optional[str] = None
    verified_last_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class WebhookPayload(BaseModel):
    raw_body: bytes
    signature: str
    headers: Dict[str, Any]
