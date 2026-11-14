from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class GoogleAuthRequest(BaseModel):
    id_token: str

class UserOut(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
