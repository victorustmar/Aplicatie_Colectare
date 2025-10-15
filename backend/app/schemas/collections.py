# from pydantic import BaseModel, Field
# from typing import Optional, Dict, Literal
# from datetime import datetime
# from uuid import UUID
#
# CollectionStatus = Literal["PENDING", "VALIDATED"]

# class CollectionCreate(BaseModel):
#     # CLIENT creează: nu trimite company_id, îl luăm din token
#     batteries: Dict[str, int] = Field(default_factory=dict)

# class CollectionOut(BaseModel):
#     collection_id: UUID
#     client_company_id: UUID
#     client_name: Optional[str] = None
#     status: CollectionStatus
#     batteries: Dict[str, int] = Field(default_factory=dict)
#     total_weight: Optional[float] = None
#     total_cost: Optional[float] = None
#     batteries_summary: Optional[str] = None
#     created_at: datetime
#     validated_at: Optional[datetime] = None


# app/schemas/collections.py
from __future__ import annotations
from typing import Dict, Optional, Any, Literal
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
# DEPRECATED: folosește app/schemas/packages.py
from .packages import (
    PackageStatus as CollectionStatus,
    PackageCreate as CollectionCreate,
    PackageOut as CollectionOut,
)


# ---- Request models ----

class BatteryLine(BaseModel):
    pcs: Optional[int] = Field(0, ge=0, description="Număr bucăți")
    weight_kg: Optional[Decimal] = Field(Decimal("0"), ge=0, description="Greutate totală (kg)")
    price_ron: Optional[Decimal] = Field(Decimal("0"), ge=0, description="Valoare totală (lei)")


class CollectionCreate(BaseModel):
    # harta cheie-tip -> liniă (ex: "3a": { pcs, weight_kg, price_ron })
    batteries: Dict[str, BatteryLine]


# ---- Response models ----
# Notă: pentru compatibilitate cu colectările vechi (unde era doar număr),
# păstrăm batteries ca Dict[str, Any] în Out.

class CollectionOut(BaseModel):
    collection_id: str
    client_company_id: str
    client_name: Optional[str] = None
    status: Literal["PENDING", "VALIDATED"]

    # Poate conține BatteryLine (nou) sau număr (vechi)
    batteries: Dict[str, Any]

    total_weight: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    batteries_summary: Optional[str] = None

    created_at: datetime
    validated_at: Optional[datetime] = None
