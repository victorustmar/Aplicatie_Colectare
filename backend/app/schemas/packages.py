from pydantic import BaseModel
from typing import Dict, Any, Optional, Literal
from datetime import datetime

PackageStatus = Literal["PENDING", "VALIDATED"]

class PackageCreate(BaseModel):
    # același payload ca vechile collections: cheie baterie -> numeric
    batteries: Dict[str, float]

class PackageOut(BaseModel):
    package_id: str
    producer_company_id: str
    status: PackageStatus
    batteries: Dict[str, Any]
    total_weight: float
    total_cost: float
    created_at: datetime
    validated_at: Optional[datetime] = None
