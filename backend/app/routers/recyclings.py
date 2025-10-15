# app/routers/recyclings.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, Dict
import uuid, json

from pydantic import BaseModel, field_validator

from app.db import get_db
from app.utils.security import get_current_user_claims

router = APIRouter(prefix="/recyclings", tags=["recyclings"])


# ---------- Schemas (noul format) ----------

class BatteryLine(BaseModel):
    pcs: Optional[int] = None           # bucăți
    weight_kg: Optional[float] = None   # kg
    price_ron: Optional[float] = None   # valoarea totală a liniei (lei)

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

    def is_empty(self) -> bool:
        return not ((self.pcs or 0) > 0 or (self.weight_kg or 0) > 0 or (self.price_ron or 0) > 0)


class RecyclingCreate(BaseModel):
    batteries: Dict[str, BatteryLine]


# ---------- Helpers ----------

def _round2(n: float) -> float:
    return float(Decimal(n).quantize(Decimal("0.01")))

def _compute_totals(lines: Dict[str, BatteryLine]) -> tuple[float, float]:
    """Returnează (total_weight, total_cost) din câmpurile weight_kg / price_ron (fără tarife automate)."""
    tw = 0.0
    tc = 0.0
    for k, ln in lines.items():
        if not isinstance(ln, BatteryLine):
            ln = BatteryLine.model_validate(ln)
        tw += float(ln.weight_kg or 0.0)
        tc += float(ln.price_ron or 0.0)
    return _round2(tw), _round2(tc)

def _lines_to_summary(lines: Dict[str, BatteryLine]) -> list[dict]:
    """Transformă bateriile în sumar pentru UI."""
    out: list[dict] = []
    for key, v in lines.items():
        ln = v if isinstance(v, BatteryLine) else BatteryLine.model_validate(v)
        qty_bits = []
        if (ln.pcs or 0) > 0:
            qty_bits.append(f"{ln.pcs} buc")
        if (ln.weight_kg or 0) > 0:
            qty_bits.append(f"{_round2(ln.weight_kg)} kg")
        qty_display = " / ".join(qty_bits) if qty_bits else "-"
        rate_display = f"{_round2(ln.price_ron)} lei" if (ln.price_ron or 0) > 0 else "-"
        out.append({
            "key": key,
            "label": key,                 # dacă ai o mapare human-friendly, o poți aplica aici
            "qty_display": qty_display,
            "rate_display": rate_display, # aici e de fapt valoarea liniei
            "line_total": _round2(ln.price_ron or 0.0),
        })
    return out


# ---------- Endpoints ----------

@router.post("", status_code=201)
def create_recycling(
    payload: RecyclingCreate,
    claims=Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    if claims.get("role") != "RECYCLER":
        raise HTTPException(status_code=403, detail="Doar utilizatorii RECICLATOR pot crea reciclări.")

    recycler_company_id = str(claims.get("company_id") or "")
    if not recycler_company_id:
        raise HTTPException(status_code=400, detail="Companie lipsă pentru utilizator.")

    # normalizează / curăță liniile goale
    clean: Dict[str, BatteryLine] = {}
    for k, v in (payload.batteries or {}).items():
        ln = BatteryLine.model_validate(v)
        if not ln.is_empty():
            clean[k] = ln
    if not clean:
        raise HTTPException(status_code=422, detail="Completează cel puțin un rând cu o valoare > 0.")

    total_w, total_c = _compute_totals(clean)

    recycling_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO recyclings(
                recycling_id, recycler_company_id, status,
                batteries, total_weight, total_cost, created_at
            )
            VALUES (:id, :cid, 'PENDING', :bats, :tw, :tc, NOW(6))
        """),
        {
            "id": recycling_id,
            "cid": recycler_company_id,
            "bats": json.dumps({k: clean[k].model_dump(exclude_none=True) for k in clean}),
            "tw": total_w,
            "tc": total_c,
        },
    )

    db.execute(
        text("""INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details)
                VALUES (:uid, :cid, 'RECYCLING_CREATED', :d)"""),
        {
            "uid": str(claims.get("sub")),
            "cid": recycler_company_id,
            "d": json.dumps({"recycling_id": recycling_id, "total_weight": total_w, "total_cost": total_c}),
        },
    )

    db.commit()
    return {"ok": True, "recycling_id": recycling_id}


# ---------------------------
# LIST
# ---------------------------
@router.get("")
def list_recyclings(
    recycler_company_id: Optional[str] = None,  # optional filter for BASE
    claims = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    role = str(claims.get("role"))
    cid  = str(claims.get("company_id") or "")

    if role == "RECYCLER":
        rows = db.execute(
            text("""
                SELECT r.recycling_id, r.recycler_company_id, r.status,
                       r.total_weight, r.total_cost, r.created_at, r.validated_at
                  FROM recyclings r
                 WHERE r.recycler_company_id = :cid
                 ORDER BY r.created_at DESC
            """),
            {"cid": cid},
        ).mappings().all()

    elif role == "BASE":
        rows = db.execute(
            text("""
                SELECT r.recycling_id, r.recycler_company_id, r.status,
                       r.total_weight, r.total_cost, r.created_at, r.validated_at,
                       c.name AS recycler_name
                  FROM recyclings r
                  JOIN relationships rel
                    ON rel.partner_company_id = r.recycler_company_id
                   AND rel.base_company_id    = :base_cid
                   AND rel.partner_type       = 'RECYCLER'
                   AND rel.status            IN ('ACTIVE','PENDING')
                  LEFT JOIN companies c ON c.company_id = r.recycler_company_id
                 WHERE (:filter_cid IS NULL OR r.recycler_company_id = :filter_cid)
                 ORDER BY r.created_at DESC
            """),
            {"base_cid": cid, "filter_cid": recycler_company_id},
        ).mappings().all()
    else:
        raise HTTPException(status_code=403, detail="Acces interzis")

    return [
        {
            "recycling_id": str(r["recycling_id"]),
            "recycler_company_id": str(r["recycler_company_id"]),
            "status": r["status"],
            "total_weight": float(r["total_weight"] or 0),
            "total_cost": float(r["total_cost"] or 0),
            "created_at": r.get("created_at"),
            "validated_at": r.get("validated_at"),
            "recycler_name": r.get("recycler_name"),
        }
        for r in rows
    ]


# ---------------------------
# GET BY ID (RECICLATOR: propriu; BASE: partenerii lui)
# ---------------------------
@router.get("/{recycling_id}")
def get_recycling(
    recycling_id: str,
    claims = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    role = str(claims.get("role"))
    cid  = str(claims.get("company_id") or "")

    if role == "RECYCLER":
        row = db.execute(
            text("""
                SELECT r.recycling_id, r.recycler_company_id, r.status,
                       r.batteries, r.total_weight, r.total_cost, r.created_at, r.validated_at,
                       c.name AS recycler_name
                  FROM recyclings r
                  LEFT JOIN companies c ON c.company_id = r.recycler_company_id
                 WHERE r.recycling_id = :rid
                   AND r.recycler_company_id = :cid
                 LIMIT 1
            """),
            {"rid": recycling_id, "cid": cid},
        ).mappings().first()

    elif role == "BASE":
        row = db.execute(
            text("""
                SELECT r.recycling_id, r.recycler_company_id, r.status,
                       r.batteries, r.total_weight, r.total_cost, r.created_at, r.validated_at,
                       c.name AS recycler_name
                  FROM recyclings r
                  JOIN relationships rel
                    ON rel.partner_company_id = r.recycler_company_id
                   AND rel.base_company_id    = :base_cid
                   AND rel.partner_type       = 'RECYCLER'
                  LEFT JOIN companies c ON c.company_id = r.recycler_company_id
                 WHERE r.recycling_id = :rid
                 LIMIT 1
            """),
            {"rid": recycling_id, "base_cid": cid},
        ).mappings().first()
    else:
        raise HTTPException(status_code=403, detail="Acces interzis")

    if not row:
        raise HTTPException(status_code=404, detail="Reciclare inexistentă sau inaccesibilă")

    bats_dict = (row.get("batteries") or {}) if isinstance(row.get("batteries"), dict) \
        else (json.loads(row["batteries"]) if row.get("batteries") else {})

    # normalize to BatteryLine and recompute summary
    norm: Dict[str, BatteryLine] = {k: BatteryLine.model_validate(v) for k, v in bats_dict.items()}
    summary = _lines_to_summary(norm)

    return {
        "recycling_id": str(row["recycling_id"]),
        "recycler_company_id": str(row["recycler_company_id"]),
        "recycler_company_name": row.get("recycler_name"),
        "status": row["status"],
        "batteries": {k: v.model_dump(exclude_none=True) for k, v in norm.items()},
        "batteries_summary": summary,
        "total_weight": float(row["total_weight"] or 0),
        "total_cost": float(row["total_cost"] or 0),
        "created_at": row.get("created_at"),
        "validated_at": row.get("validated_at"),
    }


# ---------------------------
# VALIDATE (BASE only)
# ---------------------------
@router.post("/{recycling_id}/validate")
def validate_recycling(
    recycling_id: str,
    claims = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    if str(claims.get("role")) != "BASE":
        raise HTTPException(status_code=403, detail="Doar BAZĂ poate valida reciclări")

    base_cid = str(claims.get("company_id") or "")

    ok = db.execute(
        text("""
            SELECT 1
              FROM recyclings r
              JOIN relationships rel
                ON rel.partner_company_id = r.recycler_company_id
               AND rel.base_company_id    = :base_cid
               AND rel.partner_type       = 'RECYCLER'
            WHERE r.recycling_id = :rid
            LIMIT 1
        """),
        {"base_cid": base_cid, "rid": recycling_id},
    ).scalar()

    if not ok:
        raise HTTPException(status_code=404, detail="Reciclare inexistentă sau neasociată bazei curente")

    db.execute(
        text("UPDATE recyclings SET status='VALIDATED', validated_at=NOW(6) WHERE recycling_id=:rid"),
        {"rid": recycling_id},
    )
    db.commit()

    # Returnează starea actualizată
    row = db.execute(
        text("""
            SELECT r.recycling_id, r.recycler_company_id, r.status,
                   r.total_weight, r.total_cost, r.created_at, r.validated_at
              FROM recyclings r
             WHERE r.recycling_id = :rid
        """),
        {"rid": recycling_id},
    ).mappings().first()

    return {
        "recycling_id": str(row["recycling_id"]),
        "recycler_company_id": str(row["recycler_company_id"]),
        "status": row["status"],
        "total_weight": float(row["total_weight"] or 0),
        "total_cost": float(row["total_cost"] or 0),
        "created_at": row.get("created_at"),
        "validated_at": row.get("validated_at"),
    }
