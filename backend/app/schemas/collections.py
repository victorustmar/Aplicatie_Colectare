from pydantic import BaseModel, Field
from typing import Optional, Dict, Literal
from datetime import datetime
from uuid import UUID

CollectionStatus = Literal["PENDING", "VALIDATED"]

class CollectionCreate(BaseModel):
    # CLIENT creează: nu trimite company_id, îl luăm din token
    batteries: Dict[str, int] = Field(default_factory=dict)
    total_weight: Optional[float] = None
    total_cost: Optional[float] = None

class CollectionOut(BaseModel):
    collection_id: UUID
    client_company_id: UUID
    status: CollectionStatus
    batteries: Dict[str, int] = Field(default_factory=dict)
    total_weight: Optional[float] = None
    total_cost: Optional[float] = None
    created_at: datetime
    validated_at: Optional[datetime] = None
