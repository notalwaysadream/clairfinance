from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime

class GoogleAuthRequest(BaseModel):
    id_token: Optional[str] = None
    access_token: Optional[str] = None

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
