from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    referral_code: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class ReferralCodeCreate(BaseModel):
    expiry: datetime

class ReferralCodeResponse(BaseModel):
    code: str
    expiry: datetime
    is_active: bool

class RefereeResponse(BaseModel):
    id: int
    email: EmailStr
