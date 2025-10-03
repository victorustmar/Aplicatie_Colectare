from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
class LoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    user_id: UUID
    role: str
    company_id: Optional[str] = None
    full_name: str
    company_name: Optional[str] = None

class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
