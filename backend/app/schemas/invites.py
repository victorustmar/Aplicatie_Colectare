from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal

PartnerRole = Literal["PRODUCER", "COLLECTOR", "RECYCLER"]

class CreateInviteIn(BaseModel):
    email: EmailStr
    target_role: PartnerRole
    cui: Optional[str] = None
    company_name: Optional[str] = None
    expires_in_days: int = Field(default=14, ge=1, le=90)

class InviteOut(BaseModel):
    token: str
    invite_url: str
    target_role: PartnerRole
    company: dict

class AcceptInviteIn(BaseModel):
    token: str
    password: str
    full_name: str
    phone: Optional[str] = Field(default=None, max_length=50)
