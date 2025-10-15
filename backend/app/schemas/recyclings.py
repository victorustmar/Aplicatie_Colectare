# app/schemas/recyclings.py
from pydantic import BaseModel, field_validator
from typing import Dict, Any, Optional, Literal
from datetime import datetime

RecyclingStatus = Literal["PENDING", "VALIDATED"]

class BatteryLine(BaseModel):
    pcs: Optional[int] = None          # buc
    weight_kg: Optional[float] = None  # kg
    price_ron: Optional[float] = None  # lei

    @field_validator("pcs")
    @classmethod
    def _v_pcs(cls, v):
        if v is None:
            return v
        if v < 0:
            raise ValueError("pcs must be >= 0")
        return int(v)

    @field_validator("weight_kg", "price_ron")
    @classmethod
    def _v_nonneg(cls, v):
        if v is None:
            return v
        if float(v) < 0:
            raise ValueError("value must be >= 0")
        return float(v)

class RecyclingCreate(BaseModel):
    # cheie baterie -> BatteryLine (noul format)
    batteries: Dict[str, BatteryLine]

class RecyclingOut(BaseModel):
    recycling_id: str
    recycler_company_id: str
    status: RecyclingStatus
    batteries: Dict[str, Any]
    total_weight: float
    total_cost: float
    created_at: datetime
    validated_at: Optional[datetime] = None
