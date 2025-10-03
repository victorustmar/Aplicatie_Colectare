from pydantic import BaseModel
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
    client_company_id: UUID
    collection_id: Optional[str] = None
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
    pdf_path: str | None = None
