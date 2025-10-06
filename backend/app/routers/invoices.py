from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, bindparam
from app.db import get_db
from app.utils.security import get_current_user_claims
from app.schemas.invoices import InvoiceOut, InvoiceItemOut
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(prefix="/invoices", tags=["invoices"])

@router.get("", response_model=list[InvoiceOut], response_model_exclude_none=False)
def list_invoices(claims=Depends(get_current_user_claims), db: Session = Depends(get_db)):
    role = claims.get("role")
    cid = str(claims.get("company_id"))
    if role not in ("BASE", "CLIENT"):
        raise HTTPException(403, "Rol neacceptat")

    where = "base_company_id = :cid" if role == "BASE" else "client_company_id = :cid"

    rows = db.execute(
        text(f"""
        SELECT
          invoice_id,
          base_company_id,
          client_company_id,
          collection_id,
          invoice_number,
          issue_date,
          due_date,
          currency,
          vat_rate,
          subtotal,
          vat_amount,
          total,
          status,
          created_at,
          pdf_path
        FROM invoices
        WHERE {where}
        ORDER BY created_at DESC
        """),
        {"cid": cid}
    ).mappings().all()

    ids = [r["invoice_id"] for r in rows]
    items_map = {}
    if ids:
        q = text("""
            SELECT
              item_id,
              invoice_id,
              line_no,
              description,
              qty,
              unit,
              unit_price,
              line_total
            FROM invoice_items
            WHERE invoice_id IN :ids
            ORDER BY invoice_id, line_no
        """).bindparams(bindparam("ids", expanding=True))
        items = db.execute(q, {"ids": ids}).mappings().all()
        for it in items:
            items_map.setdefault(it["invoice_id"], []).append(it)

    out: list[InvoiceOut] = []
    for r in rows:
        ro = dict(r)
        out.append(InvoiceOut(
            items=[InvoiceItemOut(**it) for it in items_map.get(ro["invoice_id"], [])],
            **ro
        ))
    return out

@router.get("/{invoice_id}", response_model=InvoiceOut, response_model_exclude_none=False)
def invoice_detail(invoice_id: str, claims=Depends(get_current_user_claims), db: Session = Depends(get_db)):
    row = db.execute(
        text("""
        SELECT
          invoice_id,
          base_company_id,
          client_company_id,
          collection_id,
          invoice_number,
          issue_date,
          due_date,
          currency,
          vat_rate,
          subtotal,
          vat_amount,
          total,
          status,
          created_at,
          pdf_path
        FROM invoices
        WHERE invoice_id = :id
        """),
        {"id": invoice_id}
    ).mappings().first()

    if not row:
        raise HTTPException(404, "Factura nu există")

    role = claims.get("role")
    cid  = str(claims.get("company_id"))
    if (role == "BASE" and row["base_company_id"] != cid) or (role == "CLIENT" and row["client_company_id"] != cid):
        raise HTTPException(403, "Nu ai acces la această primă factură")

    items = db.execute(
        text("""
        SELECT
          item_id,
          invoice_id,
          line_no,
          description,
          qty,
          unit,
          unit_price,
          line_total
        FROM invoice_items
        WHERE invoice_id = :id
        ORDER BY line_no
        """),
        {"id": invoice_id}
    ).mappings().all()

    return InvoiceOut(items=[InvoiceItemOut(**it) for it in items], **row)

@router.get("/{invoice_id}/pdf")
def download_pdf(invoice_id: str, claims=Depends(get_current_user_claims), db: Session = Depends(get_db)):
    row = db.execute(
        text("""
        SELECT
          invoice_id,
          base_company_id,
          client_company_id,
          pdf_path
        FROM invoices WHERE invoice_id = :id
        """),
        {"id": invoice_id}
    ).mappings().first()
    if not row:
        raise HTTPException(404, "Factura nu există")

    role = claims.get("role")
    cid  = str(claims.get("company_id"))
    if (role == "BASE" and row["base_company_id"] != cid) or (role == "CLIENT" and row["client_company_id"] != cid):
        raise HTTPException(403, "Nu ai acces la această factură")

    if not row["pdf_path"]:
        raise HTTPException(404, "PDF indisponibil")

    p = Path(row["pdf_path"])
    if not p.is_absolute():
        BACKEND_ROOT = Path(__file__).resolve().parents[2]
        p = (BACKEND_ROOT / p).resolve()

    if not p.exists():
        raise HTTPException(404, "PDF indisponibil")

    return FileResponse(str(p), media_type="application/pdf", filename=f"invoice-{invoice_id}.pdf")
