from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
class InviteIn(BaseModel):
    cui: str
    email: EmailStr

class CompanyMini(BaseModel):
    company_id: UUID
    cui: str
    name: Optional[str] = None
    company_code: Optional[str] = None

class InviteOut(BaseModel):
    token: str
    invite_url: str
    company: CompanyMini

class CollaborationOut(BaseModel):
    client_company_id: UUID
    cui: str
    name: Optional[str] = None
    status: str
    company_code: Optional[str] = None
