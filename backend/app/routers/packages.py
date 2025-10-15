# app/routers/packages.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import Dict, Optional
from decimal import Decimal
import uuid, json

from app.db import get_db
from app.utils.security import get_current_user_claims

router = APIRouter(prefix="/packages", tags=["packages"])

# ---------- Schemas (noul format) ----------

class BatteryLine(BaseModel):
    pcs: Optional[int] = None
    weight_kg: Optional[float] = None
    price_ron: Optional[float] = None

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


class PackageCreate(BaseModel):
    # Acceptăm (opțional) dar IGNORĂM acest câmp – folosim company_id din token.
    producer_company_id: Optional[str] = None
    batteries: Dict[str, BatteryLine]


# ---------- Helpers ----------

def _round2(n: float) -> float:
    return float(Decimal(n).quantize(Decimal("0.01")))

def _compute_totals(lines: Dict[str, BatteryLine]) -> tuple[float, float]:
    tw = 0.0
    tc = 0.0
    for k, ln in lines.items():
        if not isinstance(ln, BatteryLine):
            ln = BatteryLine.model_validate(ln)
        tw += float(ln.weight_kg or 0.0)
        tc += float(ln.price_ron or 0.0)
    return _round2(tw), _round2(tc)

def _summarize(lines: Dict[str, BatteryLine]) -> list[dict]:
    out: list[dict] = []
    for key, ln in lines.items():
        ln = ln if isinstance(ln, BatteryLine) else BatteryLine.model_validate(ln)
        qty_bits: list[str] = []
        if (ln.pcs or 0) > 0:
            qty_bits.append(f"{ln.pcs} buc")
        if (ln.weight_kg or 0) > 0:
            qty_bits.append(f"{_round2(ln.weight_kg)} kg")
        val = _round2(ln.price_ron or 0)
        out.append({
            "key": key,
            "label": key,
            "qty_display": " / ".join(qty_bits) if qty_bits else "-",
            "rate_display": f"{val:.2f} lei" if val > 0 else "-",
            "line_total": val,
        })
    return out


# ---------- Endpoints ----------

# CREATE (PRODUCER)
@router.post("", status_code=201)
def create_package(
    payload: PackageCreate,
    claims = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    if str(claims.get("role")) != "PRODUCER":
        raise HTTPException(status_code=403, detail="Doar utilizatorii PRODUCER pot crea pachete.")

    producer_cid = str(claims.get("company_id") or "")
    if not producer_cid:
        raise HTTPException(status_code=400, detail="Companie lipsă pentru utilizator.")

    # curăță liniile goale
    clean: Dict[str, BatteryLine] = {}
    for k, v in (payload.batteries or {}).items():
        ln = BatteryLine.model_validate(v)
        if not ln.is_empty():
            clean[k] = ln
    if not clean:
        raise HTTPException(status_code=422, detail="Completează cel puțin o linie cu valori > 0.")

    tw, tc = _compute_totals(clean)
    package_id = str(uuid.uuid4())

    db.execute(
        text("""
            INSERT INTO packages(
                package_id, producer_company_id, status,
                batteries, total_weight, total_cost, created_at
            )
            VALUES (:id, :p, 'PENDING', :bats, :tw, :tc, NOW(6))
        """),
        {
            "id": package_id,
            "p": producer_cid,
            "bats": json.dumps({k: clean[k].model_dump(exclude_none=True) for k in clean}),
            "tw": tw, "tc": tc,
        },
    )

    db.execute(
        text("""INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details)
                VALUES (:uid, :cid, 'PACKAGE_CREATED', :d)"""),
        {"uid": str(claims.get("sub")), "cid": producer_cid, "d": json.dumps({"package_id": package_id})},
    )
    db.commit()

    return {"ok": True, "package_id": package_id}


# LIST (BASE & PRODUCER)
@router.get("")
def list_packages(
    producer_company_id: Optional[str] = None,  # opțional pentru BAZĂ (filtru)
    claims = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    role = str(claims.get("role"))
    cid  = str(claims.get("company_id") or "")

    if role == "PRODUCER":
        rows = db.execute(
            text("""
                SELECT p.package_id, p.producer_company_id, p.status,
                       p.total_weight, p.total_cost, p.created_at, p.validated_at
                  FROM packages p
                 WHERE p.producer_company_id = :cid
                 ORDER BY p.created_at DESC
            """),
            {"cid": cid},
        ).mappings().all()

        return [
            {
                "package_id": str(r["package_id"]),
                "producer_company_id": str(r["producer_company_id"]),
                "status": r["status"],
                "total_weight": float(r["total_weight"] or 0),
                "total_cost": float(r["total_cost"] or 0),
                "created_at": r.get("created_at"),
                "validated_at": r.get("validated_at"),
            }
            for r in rows
        ]

    if role == "BASE":
        # PRODUCERi sunt legați de BAZĂ prin 'collaborations' (compat cu vechiul „client”)
        rows = db.execute(
            text("""
                SELECT p.package_id, p.producer_company_id, p.status,
                       p.total_weight, p.total_cost, p.created_at, p.validated_at,
                       c.name AS producer_name
                  FROM packages p
                  JOIN collaborations coll
                    ON coll.client_company_id = p.producer_company_id
                   AND coll.base_company_id   = :base_cid
                   AND coll.status           IN ('ACTIVE','PENDING')
                  LEFT JOIN companies c ON c.company_id = p.producer_company_id
                 WHERE (:filter_cid IS NULL OR p.producer_company_id = :filter_cid)
                 ORDER BY p.created_at DESC
            """),
            {"base_cid": cid, "filter_cid": producer_company_id},
        ).mappings().all()

        return [
            {
                "package_id": str(r["package_id"]),
                "producer_company_id": str(r["producer_company_id"]),
                "status": r["status"],
                "total_weight": float(r["total_weight"] or 0),
                "total_cost": float(r["total_cost"] or 0),
                "created_at": r.get("created_at"),
                "validated_at": r.get("validated_at"),
                "producer_name": r.get("producer_name"),
            }
            for r in rows
        ]

    raise HTTPException(status_code=403, detail="Acces interzis")


# DETAIL (BAZĂ: doar ale producătorilor săi; PRODUCER: doar ale lui)
@router.get("/{package_id}")
def get_package(
    package_id: str,
    claims = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    role = str(claims.get("role"))
    cid  = str(claims.get("company_id") or "")

    # Bază: verificăm colaborarea
    if role == "BASE":
        row = db.execute(
            text("""
                SELECT p.package_id, p.producer_company_id, p.status,
                       p.batteries, p.total_weight, p.total_cost, p.created_at, p.validated_at,
                       c.name AS producer_name
                  FROM packages p
                  JOIN collaborations coll
                    ON coll.client_company_id = p.producer_company_id
                   AND coll.base_company_id   = :base_cid
                  LEFT JOIN companies c ON c.company_id = p.producer_company_id
                 WHERE p.package_id = :pid
                 LIMIT 1
            """),
            {"pid": package_id, "base_cid": cid},
        ).mappings().first()
    elif role == "PRODUCER":
        row = db.execute(
            text("""
                SELECT p.package_id, p.producer_company_id, p.status,
                       p.batteries, p.total_weight, p.total_cost, p.created_at, p.validated_at
                  FROM packages p
                 WHERE p.package_id = :pid
                   AND p.producer_company_id = :cid
                 LIMIT 1
            """),
            {"pid": package_id, "cid": cid},
        ).mappings().first()
    else:
        raise HTTPException(status_code=403, detail="Acces interzis")

    if not row:
        raise HTTPException(status_code=404, detail="Pachet inexistent sau inaccesibil")

    bats_dict = (row.get("batteries") or {}) if isinstance(row.get("batteries"), dict) \
        else (json.loads(row["batteries"]) if row.get("batteries") else {})

    norm: Dict[str, BatteryLine] = {k: BatteryLine.model_validate(v) for k, v in bats_dict.items()}
    summary = _summarize(norm)

    resp = {
        "package_id": str(row["package_id"]),
        "producer_company_id": str(row["producer_company_id"]),
        "status": row["status"],
        "batteries": {k: v.model_dump(exclude_none=True) for k, v in norm.items()},
        "batteries_summary": summary,
        "total_weight": float(row["total_weight"] or 0),
        "total_cost": float(row["total_cost"] or 0),
        "created_at": row.get("created_at"),
        "validated_at": row.get("validated_at"),
    }
    if role == "BASE":
        resp["producer_name"] = row.get("producer_name")
    return resp


# VALIDATE (BASE only)
@router.post("/{package_id}/validate")
def validate_package(
    package_id: str,
    claims = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    if str(claims.get("role")) != "BASE":
        raise HTTPException(status_code=403, detail="Doar BAZĂ poate valida pachete")

    base_cid = str(claims.get("company_id") or "")

    # pachetul trebuie să aparțină unui producător care are colaborare cu această BAZĂ
    ok = db.execute(
        text("""
            SELECT 1
              FROM packages p
              JOIN collaborations coll
                ON coll.client_company_id = p.producer_company_id
               AND coll.base_company_id   = :base_cid
            WHERE p.package_id = :pid
            LIMIT 1
        """),
        {"base_cid": base_cid, "pid": package_id},
    ).scalar()
    if not ok:
        raise HTTPException(status_code=404, detail="Pachet inexistent sau neasociat bazei curente")

    db.execute(
        text("UPDATE packages SET status='VALIDATED', validated_at=NOW(6) WHERE package_id=:pid"),
        {"pid": package_id},
    )
    db.commit()

    row = db.execute(
        text("""
            SELECT package_id, producer_company_id, status,
                   total_weight, total_cost, created_at, validated_at
              FROM packages
             WHERE package_id = :pid
        """),
        {"pid": package_id},
    ).mappings().first()

    return {
        "package_id": str(row["package_id"]),
        "producer_company_id": str(row["producer_company_id"]),
        "status": row["status"],
        "total_weight": float(row["total_weight"] or 0),
        "total_cost": float(row["total_cost"] or 0),
        "created_at": row.get("created_at"),
        "validated_at": row.get("validated_at"),
    }
