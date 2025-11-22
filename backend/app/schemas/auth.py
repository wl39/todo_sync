from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from ..models.user import ShareMode


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserProfile(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str]
    public_slug: Optional[str]
    share_mode: ShareMode
    edit_token: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True
