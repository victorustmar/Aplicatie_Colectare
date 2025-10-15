from pydantic import BaseModel, AliasChoices, Field
from typing import List, Optional
from datetime import date, datetime
from uuid import UUID

class InvoiceItemOut(BaseModel):
    item_id: str
    line_no: int
    description: str
    qty: float
    unit: str
    unit_price: float
    line_total: float

class InvoiceOut(BaseModel):
    invoice_id: UUID
    base_company_id: UUID

    # acceptă la input atât producer_company_id (nou) cât și client_company_id (vechi),
    # dar serializează cu numele nou
    producer_company_id: UUID = Field(
        validation_alias=AliasChoices("producer_company_id", "client_company_id")
    )

    # idem: package_id (nou) vs collection_id (vechi)
    package_id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("package_id", "collection_id")
    )

    invoice_number: str
    issue_date: date
    due_date: date
    currency: str
    vat_rate: float
    subtotal: float
    vat_amount: float
    total: float
    status: str
    created_at: datetime
    items: List[InvoiceItemOut] = []
    pdf_path: Optional[str] = None

    class Config:
        populate_by_name = True
