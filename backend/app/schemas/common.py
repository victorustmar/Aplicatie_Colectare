# app/schemas/common.py
from typing import Literal
from datetime import datetime, timezone

# Roluri
Role = Literal["ADMIN", "BASE", "PRODUCER", "COLLECTOR", "RECYCLER"]
PartnerRole = Literal["PRODUCER", "COLLECTOR", "RECYCLER"]

# Statusuri
RelationshipStatus = Literal["PENDING", "ACTIVE", "REJECTED"]
PackageStatus = Literal["PENDING", "VALIDATED"]
RecyclingStatus = Literal["PENDING", "VALIDATED"]

# Helpers pentru UTC
def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

# Back-compat pentru roluri venite din sisteme mai vechi
ROLE_INVITE_REMAP = {"CLIENT": "PRODUCER", "PRODUCER": "COLLECTOR"}
def normalize_invite_role(value: str) -> PartnerRole:
    v = (value or "").upper()
    v = ROLE_INVITE_REMAP.get(v, v)
    return "PRODUCER" if v not in ("PRODUCER", "COLLECTOR", "RECYCLER") else v  # type: ignore[return-value]
