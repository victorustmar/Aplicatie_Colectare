from pydantic import BaseModel, Field
from typing import Any, Optional

class AnafLookupIn(BaseModel):
    cui: str = Field(..., description="CUI sau RO+CUI")

class AnafSummary(BaseModel):
    cui: Optional[str] = None
    denumire: Optional[str] = None
    address: Optional[str] = None      # NEW
    phone: Optional[str] = None        # NEW
    vat_payer: Optional[bool] = None
    vat_cash: Optional[bool] = None
    inactive: Optional[bool] = None
    e_invoice: Optional[bool] = None
    raw: Any = None
