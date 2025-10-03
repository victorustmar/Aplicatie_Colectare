from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID

class BillingProfile(BaseModel):
    company_id: UUID
    legal_name: str
    cui: str
    reg_com: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "RO"
    bank_name: Optional[str] = None
    iban: Optional[str] = None
    email_billing: Optional[EmailStr] = None
    phone_billing: Optional[str] = None
    vat_payer: Optional[bool] = None
    vat_cash: Optional[bool] = None
    e_invoice: Optional[bool] = None
    updated_from_anaf_at: Optional[str] = None
    source: str = "ANAF"

class BillingProfileUpdate(BaseModel):
    legal_name: Optional[str] = None
    reg_com: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    bank_name: Optional[str] = None
    iban: Optional[str] = None
    email_billing: Optional[EmailStr] = None
    phone_billing: Optional[str] = None

class InvoiceSettings(BaseModel):
    base_company_id: UUID
    series_code: str = "INV"
    next_number: int = 1
    year_reset: bool = True
    due_days: int = 15
    default_vat_rate: float = 19.0

class InvoiceSettingsUpdate(BaseModel):
    series_code: Optional[str] = None
    year_reset: Optional[bool] = None
    due_days: Optional[int] = Field(default=None, ge=0, le=120)
    default_vat_rate: Optional[float] = Field(default=None, ge=0, le=99)
    next_number: Optional[int] = Field(default=None, ge=1)
