from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import get_db
from app.utils.security import get_current_user_claims
from app.schemas.collections import CollectionCreate, CollectionOut
from app.utils.billing import billing_ready
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from app.schemas.invoices import InvoiceOut, InvoiceItemOut
import json
from pathlib import Path
from app.services.pdf import render_invoice_pdf
# add near the top of the file
import logging
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
logger = logging.getLogger("app")


router = APIRouter(prefix="/collections", tags=["collections"])

@router.post("", response_model=CollectionOut)
def create_collection(payload: CollectionCreate,
                      claims = Depends(get_current_user_claims),
                      db: Session = Depends(get_db)):
    if claims.get("role") != "CLIENT":
        raise HTTPException(403, "Doar utilizatorii CLIENT pot crea colectări")
    client_cid = claims.get("company_id")

    row = db.execute(
        text("""
            INSERT INTO collections (client_company_id, status, batteries, total_weight, total_cost)
            VALUES (:ccid, 'PENDING', CAST(:b AS JSONB), :w, :c)
            RETURNING collection_id, client_company_id, status, batteries, total_weight, total_cost, created_at, validated_at
        """),
        {
            "ccid": claims.get("company_id"),
            "b": json.dumps(payload.batteries),  # <— important!
            "w": payload.total_weight,
            "c": payload.total_cost,
        }
    ).mappings().first()

    db.execute(
        text("""INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details)
                VALUES (:uid, :cid, 'COLLECTION_CREATED', CAST(:d AS JSONB))"""),
        {
            "uid": claims.get("sub"),
            "cid": claims.get("company_id"),
            "d": json.dumps({"collection_id": str(row["collection_id"])})
        }
    )

    db.commit()
    return row

@router.get("", response_model=list[CollectionOut])
def list_collections(claims = Depends(get_current_user_claims),
                     db: Session = Depends(get_db)):
    if claims.get("role") == "CLIENT":
        return db.execute(
            text("""
            SELECT collection_id::text AS collection_id, client_company_id::text AS client_company_id, status, batteries, total_weight, total_cost, created_at, validated_at
            FROM collections
            WHERE client_company_id = :cid
            ORDER BY created_at DESC
            """),
            {"cid": claims.get("company_id")}
        ).mappings().all()

    if claims.get("role") == "BASE":
        # toate colectările clienților tăi activi/pending
        return db.execute(
            text("""
            SELECT col.collection_id::text AS collection_id,
       col.client_company_id::text AS client_company_id, col.status, col.batteries,
                   col.total_weight, col.total_cost, col.created_at, col.validated_at
              FROM collections col
              JOIN collaborations co ON co.client_company_id = col.client_company_id
             WHERE co.base_company_id = :bid
             ORDER BY col.created_at DESC
            """),
            {"bid": claims.get("company_id")}
        ).mappings().all()

    raise HTTPException(403, "Rol neacceptat")

@router.post("/{collection_id}/validate", response_model=CollectionOut)
def validate_collection(collection_id: str,
                        claims = Depends(get_current_user_claims),
                        db: Session = Depends(get_db)):
    from decimal import Decimal, ROUND_HALF_UP
    from datetime import date, timedelta
    from sqlalchemy import text
    from app.utils.billing import billing_ready

    if claims.get("role") != "BASE":
        raise HTTPException(403, "Doar utilizatorii BASE pot valida colectări")

    # 0) Citește + blochează colectarea și colaborarea
    row = db.execute(
        text("""
        SELECT  col.collection_id::text      AS collection_id,
                col.client_company_id::text  AS client_company_id,
                col.status,
                col.batteries,
                col.total_weight,
                col.total_cost,
                co.base_company_id::text     AS base_company_id,
                co.status                    AS collaboration_status
          FROM collections col
          JOIN collaborations co ON co.client_company_id = col.client_company_id
         WHERE col.collection_id = :cid
         FOR UPDATE
        """),
        {"cid": collection_id}
    ).mappings().first()

    if not row:
        raise HTTPException(404, "Colectarea nu există")
    if row["base_company_id"] != str(claims.get("company_id")):
        raise HTTPException(403, "Nu poți valida colectări care nu aparțin companiei tale")
    if row["collaboration_status"] != "ACTIVE":
        raise HTTPException(409, "Colaborarea nu este activă")
    if row["status"] == "VALIDATED":
        return row

    base_company_id   = row["base_company_id"]
    client_company_id = row["client_company_id"]

    # 1) Gard: profil & setări de facturare complete
    ok, why = billing_ready(db, base_company_id, client_company_id)
    if not ok:
        raise HTTPException(422, detail=why)

    # 2) Lock pe setările de numerotare
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

    # 3) Incrementează contorul (suntem încă în aceeași tranzacție)
    db.execute(
        text("UPDATE company_invoice_settings SET next_number = next_number + 1 WHERE base_company_id = :cid"),
        {"cid": base_company_id}
    )

    # 4) Sume
    subtotal   = Decimal(str(row["total_cost"] or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    vat_amount = (subtotal * vat_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total      = (subtotal + vat_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # 5) Creează factura
    inv_id = db.execute(
        text("""
        INSERT INTO invoices(
            base_company_id, client_company_id, collection_id,
            invoice_number, issue_date, due_date, currency,
            vat_rate, subtotal, vat_amount, total, status
        )
        VALUES(
            :b, :c, :col,
            :no, :iss, :due, 'RON',
            :vr, :sub, :vat, :tot, 'ISSUED'
        )
        RETURNING invoice_id
        """),
        {
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
    ).scalar()

    # 6) Linie simplă
    batteries  = row["batteries"] or {}
    kinds      = ", ".join(sorted(batteries.keys())) or "baterii"
    desc       = f"Colectare {kinds}"
    qty        = Decimal(str(row["total_weight"] or 1))
    if qty <= 0:
        qty = Decimal("1"); unit = "buc"; unit_price = subtotal
    else:
        unit = "kg"
        unit_price = (subtotal / qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    line_total = subtotal

    db.execute(
        text("""
        INSERT INTO invoice_items(invoice_id, line_no, description, qty, unit, unit_price, line_total)
        VALUES (:inv, 1, :desc, :qty, :unit, :price, :total)
        """),
        {"inv": inv_id, "desc": desc, "qty": str(qty), "unit": unit, "price": str(unit_price), "total": str(line_total)}
    )

    # fetch billing profiles for both parties (minimal fields)
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

    # -------  PDF GENERATION & SAVE  -------
    try:
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
        item_rows = [{
            "line_no": 1,
            "description": desc,
            "qty": str(qty),
            "unit": unit,
            "unit_price": str(unit_price),
            "line_total": str(line_total),
        }]

        # fetch minimal billing profiles (as you already do above)
        # base_profile, client_profile already loaded in your version

        pdf_bytes = render_invoice_pdf(
            invoice=invoice_dict,
            items=item_rows,
            base_profile=dict(base_profile) if base_profile else {},
            client_profile=dict(client_profile) if client_profile else {},
        )
        logger.info("PDF bytes generated for invoice %s (%d bytes)", inv_no, len(pdf_bytes))
    except Exception as e:
        logger.exception("render_invoice_pdf failed. Falling back to tiny PDF. Err: %s", e)
        # Fallback: tiny valid PDF so we still produce a file
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.drawString(72, 800, f"Invoice {inv_no}")
        c.drawString(72, 780, "PDF fallback (render error).")
        c.showPage()
        c.save()
        pdf_bytes = buf.getvalue()

    # write to disk (absolute path)
    out_dir = Path("files/invoices")
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = (out_dir / f"{inv_id}.pdf").resolve()
    pdf_path.write_bytes(pdf_bytes)
    logger.info("Wrote PDF to %s", pdf_path)

    # update DB and assert it was written
    row_update = db.execute(
        text("UPDATE invoices SET pdf_path = :p WHERE invoice_id = CAST(:id AS uuid) RETURNING pdf_path"),
        {"p": str(pdf_path), "id": str(inv_id)}
    ).mappings().first()

    if not row_update or not row_update["pdf_path"]:
        logger.error("UPDATE invoices ... RETURNING pdf_path returned nothing for %s", inv_id)
        raise HTTPException(status_code=500, detail="Nu am putut salva pdf_path în baza de date.")
    else:
        logger.info("DB updated with pdf_path=%s", row_update["pdf_path"])
    # -------  END PDF GENERATION & SAVE  -------

    # 7) Marchează VALIDATED
    db.execute(
        text("UPDATE collections SET status='VALIDATED', validated_at=now() WHERE collection_id=:cid"),
        {"cid": row["collection_id"]}
    )

    # 8) Audit
    db.execute(
        text("""INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details)
                VALUES (:uid, :cid, 'INVOICE_CREATED', CAST(:d AS JSONB))"""),
        {
            "uid": claims.get("sub"),
            "cid": base_company_id,
            "d": json.dumps({
                "collection_id": str(collection_id),
                "invoice_id": str(inv_id),
                "invoice_number": inv_no
            }),
        }
    )
    db.commit()

    # 9) Returnează colectarea (UUID -> text)
    out = db.execute(
        text("""
        SELECT collection_id::text AS collection_id,
               client_company_id::text AS client_company_id,
               status, batteries, total_weight, total_cost, created_at, validated_at
          FROM collections
         WHERE collection_id = :cid
        """),
        {"cid": row["collection_id"]}
    ).mappings().first()

    # IMPORTANT: nu facem commit aici dacă get_db() se ocupă de commit/rollback
    return out

