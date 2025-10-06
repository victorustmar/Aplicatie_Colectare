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
from app.utils.rates import (
    PORTABLE_KEYS, KG_KEYS, LABELS,
    PORTABLE_RATES, PORTABLE_WEIGHTS_KG, KG_RATES,
)
router = APIRouter(prefix="/collections", tags=["collections"])

# ----- Helpers ---------------------------------------------------------------

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

from decimal import Decimal

def _batteries_summary(bats: dict[str, int]) -> str:
    items = []
    for k, v in bats.items():
        if isinstance(v, (int, float, Decimal)) and v:
            items.append(f"{k}: {v}")
    return ", ".join(items) if items else ""

# Tarife „sursa de adevăr” pe server (exemplu; ajustează după cum e în business)
PORTABLE_RATES = {
    "portable_pastila":   Decimal("0.01"),
    "portable_0_50":      Decimal("0.04"),
    "portable_51_150":    Decimal("0.11"),
    "portable_151_250":   Decimal("0.38"),
    "portable_251_500":   Decimal("0.80"),
    "portable_501_750":   Decimal("0.98"),
    "portable_751_1000":  Decimal("1.20"),
    "portable_1000_plus": Decimal("1.38"),
}
PORTABLE_WEIGHTS_KG = {
    "portable_pastila":   Decimal("0.010"),
    "portable_0_50":      Decimal("0.050"),
    "portable_51_150":    Decimal("0.150"),
    "portable_151_250":   Decimal("0.250"),
    "portable_251_500":   Decimal("0.500"),
    "portable_501_750":   Decimal("0.750"),
    "portable_751_1000":  Decimal("1.000"),
    "portable_1000_plus": Decimal("1.000"),
}
KG_RATES = {
    "auto_3a":        Decimal("0.35"),
    "auto_3b":        Decimal("1.38"),
    "auto_3c":        Decimal("1.38"),
    "industrial_4a":  Decimal("0.35"),
    "industrial_4b":  Decimal("1.38"),
    "industrial_4c":  Decimal("1.38"),
}

def _compute_server_totals(bats: dict[str, int]) -> tuple[Decimal, Decimal]:
    # return (subtotal RON, total_weight kg); ambele rotunjite la 2 zecimale pt. stocare/afișare
    subtotal = Decimal("0")
    total_w = Decimal("0")

    # portable = pe bucată
    for key, rate in PORTABLE_RATES.items():
        qty = Decimal(str(bats.get(key, 0) or 0))
        if qty > 0:
            subtotal += qty * rate
            total_w += qty * PORTABLE_WEIGHTS_KG.get(key, Decimal("0"))

    # auto/industrial = cantitatea introdusă este deja în kg
    for key, rate in KG_RATES.items():
        kg = Decimal(str(bats.get(key, 0) or 0))
        if kg > 0:
            subtotal += kg * rate
            total_w += kg

    q2 = lambda x: x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return q2(subtotal), q2(total_w)

def _fetch_collection(db: Session, cid: str) -> dict | None:
    rec = db.execute(
        text("""SELECT collection_id, client_company_id, status, batteries,
                       total_weight, total_cost, created_at, validated_at
                FROM collections
               WHERE collection_id = :cid"""),
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
    claims = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    client_company_id = claims.get("company_id")
    if not client_company_id:
        raise HTTPException(status_code=422, detail="Fără firmă asociată")

    # 1) Normalizează JSON-ul
    bats = _parse_json(payload.batteries)

    # 2) Calculează server-side total_weight & total_cost
    subtotal, total_w = _compute_server_totals(bats)

    # 3) Inserează
    db.execute(
        text("""INSERT INTO collections (client_company_id, status, batteries, total_weight, total_cost)
                VALUES (:cid, 'PENDING', :bats, :w, :c)"""),
        {
            "cid": client_company_id,
            "bats": json.dumps(bats),
            "w": str(total_w),
            "c": str(subtotal),
        }
    )
    db.commit()

    # 4) Returnează ultimul rând al clientului (sau FETCH BY ID dacă preferi)
    row = db.execute(
        text("""SELECT collection_id, client_company_id, status, batteries,
                       total_weight, total_cost, created_at, validated_at
                FROM collections
                WHERE client_company_id = :cid
                ORDER BY created_at DESC
                LIMIT 1"""),
        {"cid": client_company_id}
    ).mappings().first()

    result = dict(row)
    result["batteries"] = _parse_json(result["batteries"])
    result["batteries_summary"] = _batteries_summary(result["batteries"])
    return result

@router.get("", response_model=list[CollectionOut])
def list_collections(
    claims = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    role = claims.get("role")
    company_id = claims.get("company_id")
    if not company_id:
        return []

    if role == "CLIENT":
        rows = db.execute(
            text("""SELECT collection_id, client_company_id, status, batteries,
                           total_weight, total_cost, created_at, validated_at
                    FROM collections
                   WHERE client_company_id = :cid
                   ORDER BY created_at DESC"""),
            {"cid": company_id},
        ).mappings().all()

    elif role == "BASE":
        rows = db.execute(
            text("""SELECT c.collection_id, c.client_company_id, comp.name AS client_name, c.status, c.batteries,
                           c.total_weight, c.total_cost, c.created_at, c.validated_at
                      FROM collections AS c
                INNER JOIN collaborations AS col
                        ON col.client_company_id = c.client_company_id
                      LEFT JOIN companies AS comp                         -- ← JOIN lipsă
                ON comp.company_id = c.client_company_id
                     WHERE col.base_company_id = :cid
                       AND col.status = 'ACTIVE'
                  ORDER BY c.created_at DESC"""),
            {"cid": company_id},
        ).mappings().all()

    elif role == "ADMIN":
        rows = db.execute(
            text("""SELECT collection_id, client_company_id, status, batteries,
                           total_weight, total_cost, created_at, validated_at
                      FROM collections
                  ORDER BY created_at DESC""")
        ).mappings().all()
    else:
        rows = []

    result = []
    for r in rows:
        bats = _parse_json(r["batteries"])
        result.append({
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
        })
    return result

@router.get("/{collection_id}", response_model=CollectionOut)
def get_collection(
    collection_id: str,
    claims = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    role = claims.get("role")
    company_id = claims.get("company_id")

    if role == "CLIENT":
        row = db.execute(
            text("""SELECT collection_id, client_company_id, status, batteries,
                           total_weight, total_cost, created_at, validated_at
                      FROM collections
                     WHERE collection_id = :cid
                       AND client_company_id = :ccid"""),
            {"cid": collection_id, "ccid": company_id},
        ).mappings().first()

    elif role == "BASE":
        row = db.execute(
            text("""SELECT c.collection_id, c.client_company_id, c.status, c.batteries,
                           c.total_weight, c.total_cost, c.created_at, c.validated_at
                      FROM collections c
                      JOIN collaborations col
                        ON col.client_company_id = c.client_company_id
                     WHERE c.collection_id = :cid
                       AND col.base_company_id = :bcid"""),
            {"cid": collection_id, "bcid": company_id},
        ).mappings().first()

    elif role == "ADMIN":
        row = db.execute(
            text("""SELECT collection_id, client_company_id, status, batteries,
                           total_weight, total_cost, created_at, validated_at
                      FROM collections
                     WHERE collection_id = :cid"""),
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
def validate_collection(
    collection_id: str,
    claims = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    if claims.get("role") != "BASE":
        raise HTTPException(403, "Doar utilizatorii BASE pot valida colectări")

    row = db.execute(
        text("""
        SELECT  col.collection_id,
                col.client_company_id,
                col.status,
                col.batteries,
                col.total_weight,
                col.total_cost,
                co.base_company_id,
                co.status AS collaboration_status
          FROM collections col
          JOIN collaborations co ON co.client_company_id = col.client_company_id
         WHERE col.collection_id = :cid
         FOR UPDATE
        """),
        {"cid": collection_id}
    ).mappings().first()

    if not row:
        raise HTTPException(404, "Colectarea nu există")
    if str(row["base_company_id"]) != str(claims.get("company_id")):
        raise HTTPException(403, "Nu poți valida colectări care nu aparțin companiei tale")
    if row["collaboration_status"] != "ACTIVE":
        raise HTTPException(409, "Colaborarea nu este activă")

    # dacă e deja validată, întoarce-o normalizată
    if row["status"] == "VALIDATED":
        col = _fetch_collection(db, row["collection_id"])
        if not col:
            raise HTTPException(404, "Colectarea nu există")
        return col

    base_company_id   = str(row["base_company_id"])
    client_company_id = str(row["client_company_id"])

    ok, why = billing_ready(db, base_company_id, client_company_id)
    if not ok:
        raise HTTPException(422, detail=why)

    sett = db.execute(
        text("""
        SELECT base_company_id, series_code, next_number, year_reset, due_days, default_vat_rate
          FROM company_invoice_settings
         WHERE base_company_id = :cid
         FOR UPDATE
        """),
        {"cid": base_company_id}
    ).mappings().first()
    if not sett:
        raise HTTPException(422, detail="Lipsește configurarea de numerotare pentru BAZĂ")

    series     = sett["series_code"] or "INV"
    num        = int(sett["next_number"] or 1)
    year_reset = bool(sett["year_reset"])
    due_days   = int(sett["due_days"] or 15)
    vat_rate   = Decimal(str(sett["default_vat_rate"] or 19))

    today  = date.today()
    inv_no = f"{series}-{today.year}-{num:06d}" if year_reset else f"{series}-{num:06d}"

    # rezervăm numărul
    db.execute(
        text("UPDATE company_invoice_settings SET next_number = next_number + 1 WHERE base_company_id = :cid"),
        {"cid": base_company_id}
    )

    # -------- construiți liniile din baterii --------
    batteries = _parse_json(row["batteries"] or {})

    def q2(n: Decimal) -> Decimal:
        return n.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    lines: list[dict] = []
    subtotal = Decimal("0")
    total_weight = Decimal("0")

    # portabile (buc)
    for key in PORTABLE_KEYS:
        qty_raw = batteries.get(key) or 0
        qty = Decimal(str(qty_raw))
        if qty <= 0:
            continue
        unit_price = Decimal(str(PORTABLE_RATES[key]))
        line_total = q2(qty * unit_price)
        weight_kg  = q2(qty * Decimal(str(PORTABLE_WEIGHTS_KG[key])))

        lines.append({
            "description": f"{LABELS[key]} (portabil)",
            "qty": qty,
            "unit": "buc",
            "unit_price": unit_price,
            "line_total": line_total,
            "weight_kg": weight_kg,
        })
        subtotal     += line_total
        total_weight += weight_kg

    # auto/industrial (kg)
    for key in KG_KEYS:
        w_raw = batteries.get(key) or 0
        w = Decimal(str(w_raw))
        if w <= 0:
            continue
        unit_price = Decimal(str(KG_RATES[key]))
        line_total = q2(w * unit_price)

        lines.append({
            "description": LABELS[key],
            "qty": w,
            "unit": "kg",
            "unit_price": unit_price,
            "line_total": line_total,
            "weight_kg": w,
        })
        subtotal     += line_total
        total_weight += w

    subtotal   = q2(subtotal)
    vat_amount = q2(subtotal * vat_rate / Decimal("100"))
    total      = q2(subtotal + vat_amount)

    # sincronizează totalurile în colecție (opțional, dar util)
    db.execute(
        text("""UPDATE collections
                   SET total_weight = :tw, total_cost = :tc
                 WHERE collection_id = :cid"""),
        {"tw": str(total_weight), "tc": str(subtotal), "cid": row["collection_id"]},
    )

    # -------- header factură --------
    inv_id = str(uuid.uuid4())
    db.execute(
        text("""
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
        """),
        {
            "id": inv_id,
            "b": base_company_id,
            "c": client_company_id,
            "col": row["collection_id"],
            "no": inv_no,
            "iss": today,
            "due": today + timedelta(days=due_days),
            "vr": str(vat_rate),
            "sub": str(subtotal),
            "vat": str(vat_amount),
            "tot": str(total),
        }
    )

    # -------- linii factură --------
    line_no = 1
    for ln in lines:
        db.execute(
            text("""
            INSERT INTO invoice_items (invoice_id, line_no, description, qty, unit, unit_price, line_total)
            VALUES (:inv, :no, :desc, :qty, :unit, :price, :total)
            """),
            {
                "inv": inv_id,
                "no": line_no,
                "desc": ln["description"],
                "qty": str(q2(Decimal(str(ln["qty"])))),
                "unit": ln["unit"],
                "price": str(q2(Decimal(str(ln["unit_price"])))),
                "total": str(q2(Decimal(str(ln["line_total"])))),
            }
        )
        line_no += 1

    # profile pentru PDF
    base_profile = db.execute(text("""
      SELECT c.name AS company_name, c.cui, p.legal_name, p.address_line, p.city, p.county,
             p.postal_code, COALESCE(p.country,'RO') AS country, p.bank_name, p.iban,
             p.email_billing, p.phone_billing
        FROM companies c
        LEFT JOIN company_billing_profiles p ON p.company_id = c.company_id
       WHERE c.company_id = :cid
    """), {"cid": base_company_id}).mappings().first()

    client_profile = db.execute(text("""
      SELECT c.name AS company_name, c.cui, p.legal_name, p.address_line, p.city, p.county,
             p.postal_code, COALESCE(p.country,'RO') AS country, p.bank_name, p.iban,
             p.email_billing, p.phone_billing
        FROM companies c
        LEFT JOIN company_billing_profiles p ON p.company_id = c.company_id
       WHERE c.company_id = :cid
    """), {"cid": client_company_id}).mappings().first()

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

    # pregătește linii pentru PDF (include și greutatea, dacă vrei să o afișezi)
    pdf_items = []
    for i, ln in enumerate(lines, start=1):
        pdf_items.append({
            "line_no": i,
            "description": ln["description"],
            "qty": str(q2(Decimal(str(ln["qty"])))),
            "unit": ln["unit"],
            "unit_price": str(q2(Decimal(str(ln["unit_price"])))),
            "line_total": str(q2(Decimal(str(ln["line_total"])))),
            "weight_kg": str(q2(Decimal(str(ln["weight_kg"])))),
        })

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

    db.execute(
        text("UPDATE invoices SET pdf_path = :p WHERE invoice_id = :id"),
        {"p": str(pdf_path), "id": inv_id}
    )

    db.execute(
        text("UPDATE collections SET status='VALIDATED', validated_at=NOW(6) WHERE collection_id=:cid"),
        {"cid": row["collection_id"]}
    )

    db.execute(
        text("""INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details)
                VALUES (:uid, :cid, 'INVOICE_CREATED', :d)"""),
        {
            "uid": str(claims.get("sub")),
            "cid": base_company_id,
            "d": json.dumps({
                "collection_id": str(collection_id),
                "invoice_id": inv_id,
                "invoice_number": inv_no
            }),
        }
    )
    db.commit()

    col = _fetch_collection(db, row["collection_id"])
    if not col:
        raise HTTPException(404, "Colectarea nu există (după validare)")
    return col
