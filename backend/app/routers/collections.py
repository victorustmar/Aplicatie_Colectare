from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import get_db
from app.utils.security import get_current_user_claims
from app.schemas.collections import CollectionCreate, CollectionOut
from app.utils.billing import billing_ready
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
import uuid, json
from pathlib import Path
from app.services.pdf import render_invoice_pdf
from app.utils.rates import LABELS
from pydantic import BaseModel  # pentru detectare linii Pydantic

router = APIRouter(prefix="/collections", tags=["collections"])

# ----- Helpers (nemodificate semnificativ) ----------------------------------

def _parse_json(value):
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode()
        except Exception:
            return {}
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {}
    return {}

def _as_plain_dict(obj) -> dict:
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, BaseModel):
        return obj.model_dump() if hasattr(obj, "model_dump") else obj.dict()
    return {}

def _normalize_line(val) -> dict:
    if isinstance(val, (int, float, Decimal)):
        return {"pcs": int(val), "weight_kg": Decimal("0"), "price_ron": Decimal("0")}
    if isinstance(val, (BaseModel, dict)):
        d = _as_plain_dict(val)
    elif isinstance(val, (str, bytes, bytearray)):
        d = _parse_json(val)
    else:
        d = {}

    pcs = int(d.get("pcs") or d.get("pieces") or 0)
    weight = Decimal(str(d.get("weight_kg") or 0))
    price = Decimal(str(d.get("price_ron") or d.get("price") or 0))
    return {"pcs": pcs, "weight_kg": weight, "price_ron": price}

def _normalize_batteries(bats: dict | None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for k, raw in (bats or {}).items():
        ln = _normalize_line(raw)
        if ln["pcs"] or ln["weight_kg"] or ln["price_ron"]:
            out[str(k)] = {
                "pcs": int(ln["pcs"]),
                "weight_kg": float(ln["weight_kg"]),
                "price_ron": float(ln["price_ron"]),
            }
    return out

def _batteries_summary(bats: dict) -> str:
    items = []
    for k, raw in (bats or {}).items():
        ln = _normalize_line(raw)
        if not (ln["pcs"] or ln["weight_kg"] or ln["price_ron"]):
            continue
        label = LABELS.get(k, k)
        seg = []
        if ln["pcs"]:
            seg.append(f"{ln['pcs']} buc")
        if ln["weight_kg"]:
            seg.append(f"{ln['weight_kg']} kg")
        if ln["price_ron"]:
            seg.append(f"{ln['price_ron']} lei")
        items.append(f"{label}: " + ", ".join(seg))
    return "; ".join(items)

def _compute_server_totals(bats: dict) -> tuple[Decimal, Decimal]:
    subtotal = Decimal("0")
    total_w = Decimal("0")
    for _, raw in (bats or {}).items():
        ln = _normalize_line(raw)
        subtotal += ln["price_ron"]
        total_w += ln["weight_kg"]

    q2 = lambda x: x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return q2(subtotal), q2(total_w)

def _fetch_collection(db: Session, cid: str) -> dict | None:
    rec = db.execute(
        text(
            """SELECT collection_id, client_company_id, status, batteries,
                       total_weight, total_cost, created_at, validated_at
                FROM collections
               WHERE collection_id = :cid"""
        ),
        {"cid": cid},
    ).mappings().first()
    if not rec:
        return None
    bats = _parse_json(rec["batteries"])
    out = dict(rec)
    out["batteries"] = bats
    out["batteries_summary"] = _batteries_summary(bats)
    return out

# ----- Endpoints -------------------------------------------------------------

@router.post("", response_model=CollectionOut)
def create_collection(
    payload: CollectionCreate,
    claims=Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    # a fost: CLIENT; acum: PRODUCER
    if claims.get("role") != "PRODUCER":
        raise HTTPException(status_code=403, detail="Doar utilizatorii PRODUCER pot crea pachete (colectări).")

    producer_company_id = claims.get("company_id")
    if not producer_company_id:
        raise HTTPException(status_code=422, detail="Fără firmă asociată")

    raw_bats = _parse_json(payload.batteries)
    bats_norm = _normalize_batteries(raw_bats)

    subtotal, total_w = _compute_server_totals(bats_norm)

    db.execute(
        text(
            """INSERT INTO collections (client_company_id, status, batteries, total_weight, total_cost)
                VALUES (:cid, 'PENDING', :bats, :w, :c)"""
        ),
        {"cid": producer_company_id, "bats": json.dumps(bats_norm), "w": str(total_w), "c": str(subtotal)},
    )
    db.commit()

    row = db.execute(
        text(
            """SELECT collection_id, client_company_id, status, batteries,
                       total_weight, total_cost, created_at, validated_at
                FROM collections
                WHERE client_company_id = :cid
                ORDER BY created_at DESC
                LIMIT 1"""
        ),
        {"cid": producer_company_id},
    ).mappings().first()

    result = dict(row)
    result["batteries"] = _parse_json(result["batteries"])
    result["batteries_summary"] = _batteries_summary(result["batteries"])
    return result

@router.get("", response_model=list[CollectionOut])
def list_collections(claims=Depends(get_current_user_claims), db: Session = Depends(get_db)):
    role = claims.get("role")
    company_id = claims.get("company_id")
    if not company_id:
        return []

    if role == "PRODUCER":
        rows = db.execute(
            text(
                """SELECT collection_id, client_company_id, status, batteries,
                           total_weight, total_cost, created_at, validated_at
                    FROM collections
                   WHERE client_company_id = :cid
                   ORDER BY created_at DESC"""
            ),
            {"cid": company_id},
        ).mappings().all()

    elif role == "BASE":
        rows = db.execute(
            text(
                """SELECT c.collection_id, c.client_company_id, comp.name AS client_name, c.status, c.batteries,
                           c.total_weight, c.total_cost, c.created_at, c.validated_at
                      FROM collections AS c
                INNER JOIN relationships AS rel
                        ON rel.partner_company_id = c.client_company_id
                       AND rel.base_company_id   = :cid
                       AND rel.partner_type      = 'PRODUCER'
                       AND rel.status            = 'ACTIVE'
                      LEFT JOIN companies AS comp
                        ON comp.company_id = c.client_company_id
                  ORDER BY c.created_at DESC"""
            ),
            {"cid": company_id},
        ).mappings().all()

    elif role == "ADMIN":
        rows = db.execute(
            text(
                """SELECT collection_id, client_company_id, status, batteries,
                           total_weight, total_cost, created_at, validated_at
                      FROM collections
                  ORDER BY created_at DESC"""
            )
        ).mappings().all()
    else:
        rows = []

    result = []
    for r in rows:
        bats = _parse_json(r["batteries"])
        result.append(
            {
                "collection_id": str(r["collection_id"]),
                "client_company_id": str(r["client_company_id"]),
                "client_name": r.get("client_name"),
                "status": r["status"],
                "batteries": bats,
                "batteries_summary": _batteries_summary(bats),
                "total_weight": r["total_weight"],
                "total_cost": r["total_cost"],
                "created_at": r["created_at"],
                "validated_at": r["validated_at"],
            }
        )
    return result

@router.get("/{collection_id}", response_model=CollectionOut)
def get_collection(collection_id: str, claims=Depends(get_current_user_claims), db: Session = Depends(get_db)):
    role = claims.get("role")
    company_id = claims.get("company_id")

    if role == "PRODUCER":
        row = db.execute(
            text(
                """SELECT collection_id, client_company_id, status, batteries,
                           total_weight, total_cost, created_at, validated_at
                      FROM collections
                     WHERE collection_id = :cid
                       AND client_company_id = :ccid"""
            ),
            {"cid": collection_id, "ccid": company_id},
        ).mappings().first()

    elif role == "BASE":
        row = db.execute(
            text(
                """SELECT c.collection_id, c.client_company_id, c.status, c.batteries,
                           c.total_weight, c.total_cost, c.created_at, c.validated_at
                      FROM collections c
                      JOIN relationships rel
                        ON rel.partner_company_id = c.client_company_id
                       AND rel.base_company_id    = :bcid
                       AND rel.partner_type       = 'PRODUCER'
                     WHERE c.collection_id = :cid"""
            ),
            {"cid": collection_id, "bcid": company_id},
        ).mappings().first()

    elif role == "ADMIN":
        row = db.execute(
            text(
                """SELECT collection_id, client_company_id, status, batteries,
                           total_weight, total_cost, created_at, validated_at
                      FROM collections
                     WHERE collection_id = :cid"""
            ),
            {"cid": collection_id},
        ).mappings().first()
    else:
        raise HTTPException(403, "Neautorizat")

    if not row:
        raise HTTPException(404, "Colectarea nu există")

    bats = _parse_json(row["batteries"])
    return {
        "collection_id": str(row["collection_id"]),
        "client_company_id": str(row["client_company_id"]),
        "status": row["status"],
        "batteries": bats,
        "batteries_summary": _batteries_summary(bats),
        "total_weight": row["total_weight"],
        "total_cost": row["total_cost"],
        "created_at": row["created_at"],
        "validated_at": row["validated_at"],
    }

@router.post("/{collection_id}/validate", response_model=CollectionOut)
def validate_collection(collection_id: str, claims=Depends(get_current_user_claims), db: Session = Depends(get_db)):
    if claims.get("role") != "BASE":
        raise HTTPException(403, "Doar utilizatorii BASE pot valida colectări")

    row = db.execute(
        text(
            """
        SELECT  col.collection_id,
                col.client_company_id,
                col.status,
                col.batteries,
                col.total_weight,
                col.total_cost,
                rel.base_company_id,
                rel.status AS relationship_status
          FROM collections col
          JOIN relationships rel
            ON rel.partner_company_id = col.client_company_id
           AND rel.partner_type       = 'PRODUCER'
         WHERE col.collection_id = :cid
         FOR UPDATE
        """
        ),
        {"cid": collection_id},
    ).mappings().first()

    if not row:
        raise HTTPException(404, "Colectarea nu există")
    if str(row["base_company_id"]) != str(claims.get("company_id")):
        raise HTTPException(403, "Nu poți valida colectări care nu aparțin companiei tale")
    if row["relationship_status"] != "ACTIVE":
        raise HTTPException(409, "Relația nu este activă")

    # dacă e deja validată, întoarce-o normalizată
    if row["status"] == "VALIDATED":
        col = _fetch_collection(db, row["collection_id"])
        if not col:
            raise HTTPException(404, "Colectarea nu există")
        return col

    base_company_id   = str(row["base_company_id"])
    producer_company_id = str(row["client_company_id"])

    ok, why = billing_ready(db, base_company_id, producer_company_id)
    if not ok:
        raise HTTPException(422, detail=why)

    sett = db.execute(
        text(
            """
        SELECT base_company_id, series_code, next_number, year_reset, due_days, default_vat_rate
          FROM company_invoice_settings
         WHERE base_company_id = :cid
         FOR UPDATE
        """
        ),
        {"cid": base_company_id},
    ).mappings().first()
    if not sett:
        raise HTTPException(422, detail="Lipsește configurarea de numerotare pentru BAZĂ")

    series = sett["series_code"] or "INV"
    num = int(sett["next_number"] or 1)
    year_reset = bool(sett["year_reset"])
    due_days = int(sett["due_days"] or 15)
    vat_rate = Decimal(str(sett["default_vat_rate"] or 19))

    today = date.today()
    inv_no = f"{series}-{today.year}-{num:06d}" if year_reset else f"{series}-{num:06d}"

    # rezervăm numărul
    db.execute(
        text("UPDATE company_invoice_settings SET next_number = next_number + 1 WHERE base_company_id = :cid"),
        {"cid": base_company_id},
    )

    batteries = _parse_json(row["batteries"] or {})

    def q2(n: Decimal) -> Decimal:
        return n.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    lines: list[dict] = []
    subtotal = Decimal("0")
    total_weight = Decimal("0")

    for key, raw in (batteries or {}).items():
        ln = _normalize_line(raw)
        if not (ln["pcs"] or ln["weight_kg"] or ln["price_ron"]):
            continue

        if ln["weight_kg"] > 0:
            qty = ln["weight_kg"]
            unit = "kg"
        else:
            qty = Decimal(str(ln["pcs"] or 0))
            unit = "buc"

        line_total = q2(ln["price_ron"])
        unit_price = q2(line_total / qty) if qty and qty > 0 else line_total

        lines.append(
            {
                "description": LABELS.get(key, key),
                "qty": qty,
                "unit": unit,
                "unit_price": unit_price,
                "line_total": line_total,
                "weight_kg": ln["weight_kg"],
            }
        )
        subtotal += line_total
        total_weight += ln["weight_kg"]

    subtotal = q2(subtotal)
    vat_amount = q2(subtotal * vat_rate / Decimal("100"))
    total = q2(subtotal + vat_amount)

    # sincronizează totalurile în colecție
    db.execute(
        text(
            """UPDATE collections
                   SET total_weight = :tw, total_cost = :tc
                 WHERE collection_id = :cid"""
        ),
        {"tw": str(total_weight), "tc": str(subtotal), "cid": row["collection_id"]},
    )

    # header factură
    inv_id = str(uuid.uuid4())
    db.execute(
        text(
            """
        INSERT INTO invoices(
            invoice_id, base_company_id, client_company_id, collection_id,
            invoice_number, issue_date, due_date, currency,
            vat_rate, subtotal, vat_amount, total, status
        )
        VALUES(
            :id, :b, :c, :col,
            :no, :iss, :due, 'RON',
            :vr, :sub, :vat, :tot, 'ISSUED'
        )
        """
        ),
        {
            "id": inv_id,
            "b": base_company_id,
            "c": producer_company_id,
            "col": row["collection_id"],
            "no": inv_no,
            "iss": today,
            "due": today + timedelta(days=due_days),
            "vr": str(vat_rate),
            "sub": str(subtotal),
            "vat": str(vat_amount),
            "tot": str(total),
        },
    )

    # linii factură
    line_no = 1
    for ln in lines:
        db.execute(
            text(
                """
            INSERT INTO invoice_items (invoice_id, line_no, description, qty, unit, unit_price, line_total)
            VALUES (:inv, :no, :desc, :qty, :unit, :price, :total)
            """
            ),
            {
                "inv": inv_id,
                "no": line_no,
                "desc": ln["description"],
                "qty": str(q2(Decimal(str(ln["qty"])))),
                "unit": ln["unit"],
                "price": str(q2(Decimal(str(ln["unit_price"])))),
                "total": str(q2(Decimal(str(ln["line_total"])))),
            },
        )
        line_no += 1

    # profile PDF
    base_profile = db.execute(
        text(
            """
      SELECT c.name AS company_name, c.cui, p.legal_name, p.address_line, p.city, p.county,
             p.postal_code, COALESCE(p.country,'RO') AS country, p.bank_name, p.iban,
             p.email_billing, p.phone_billing
        FROM companies c
        LEFT JOIN company_billing_profiles p ON p.company_id = c.company_id
       WHERE c.company_id = :cid
    """
        ),
        {"cid": base_company_id},
    ).mappings().first()

    client_profile = db.execute(
        text(
            """
      SELECT c.name AS company_name, c.cui, p.legal_name, p.address_line, p.city, p.county,
             p.postal_code, COALESCE(p.country,'RO') AS country, p.bank_name, p.iban,
             p.email_billing, p.phone_billing
        FROM companies c
        LEFT JOIN company_billing_profiles p ON p.company_id = c.company_id
       WHERE c.company_id = :cid
    """
        ),
        {"cid": producer_company_id},
    ).mappings().first()

    invoice_dict = {
        "invoice_number": inv_no,
        "issue_date": today.isoformat(),
        "due_date": (today + timedelta(days=due_days)).isoformat(),
        "currency": "RON",
        "vat_rate": str(vat_rate),
        "subtotal": str(subtotal),
        "vat_amount": str(vat_amount),
        "total": str(total),
    }

    def q2s(x: Decimal) -> str:
        return str(x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    pdf_items = []
    for i, ln in enumerate(lines, start=1):
        pdf_items.append(
            {
                "line_no": i,
                "description": ln["description"],
                "qty": q2s(Decimal(str(ln["qty"]))),
                "unit": ln["unit"],
                "unit_price": q2s(Decimal(str(ln["unit_price"]))),
                "line_total": q2s(Decimal(str(ln["line_total"]))),
                "weight_kg": q2s(Decimal(str(ln["weight_kg"]))),
            }
        )

    pdf_bytes = render_invoice_pdf(
        invoice=invoice_dict,
        items=pdf_items,
        base_profile=dict(base_profile) if base_profile else {},
        client_profile=dict(client_profile) if client_profile else {},
    )

    out_dir = Path("files/invoices")
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f"{inv_id}.pdf"
    pdf_path.write_bytes(pdf_bytes)

    db.execute(text("UPDATE invoices SET pdf_path = :p WHERE invoice_id = :id"), {"p": str(pdf_path), "id": inv_id})

    db.execute(
        text("UPDATE collections SET status='VALIDATED', validated_at=NOW(6) WHERE collection_id=:cid"),
        {"cid": row["collection_id"]},
    )

    db.execute(
        text(
            """INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details)
                VALUES (:uid, :cid, 'INVOICE_CREATED', :d)"""
        ),
        {
            "uid": str(claims.get("sub")),
            "cid": base_company_id,
            "d": json.dumps({"collection_id": str(collection_id), "invoice_id": inv_id, "invoice_number": inv_no}),
        },
    )
    db.commit()

    col = _fetch_collection(db, row["collection_id"])
    if not col:
        raise HTTPException(404, "Colectarea nu există (după validare)")
    return col
