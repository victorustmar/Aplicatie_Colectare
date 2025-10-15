# app/schemas/auth.py
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr

Role = Literal["ADMIN", "BASE", "PRODUCER", "COLLECTOR", "RECYCLER"]

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    user_id: str
    role: Role
    company_id: Optional[str] = None
    full_name: Optional[str] = None
    company_name: Optional[str] = None

# Back-compat with any places importing `User`
class User(UserOut):
    pass

class LoginOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserOut
