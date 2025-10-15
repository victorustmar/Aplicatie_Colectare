from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import date
import httpx, secrets, json, uuid

from app.db import get_db
from app.utils.security import get_current_user_claims
from app.schemas.companies import InviteIn, InviteOut, CompanyMini, CollaborationOut
from app.config import settings
from .anaf import _sanitize_cui
from app.utils.billing import upsert_billing_profile_from_anaf

router = APIRouter(prefix="/companies", tags=["companies"])

def _token() -> str:
    return secrets.token_urlsafe(32)

@router.post("/invite", response_model=InviteOut)
async def invite_company(payload: InviteIn, request: Request,
                         claims = Depends(get_current_user_claims),
                         db: Session = Depends(get_db)):

    # doar BAZA poate invita
    if claims.get("role") != "BASE":
        raise HTTPException(status_code=403, detail="Doar utilizatorii BASE pot invita")
    base_cid = str(claims.get("company_id"))
    if not base_cid:
        raise HTTPException(status_code=400, detail="Lipsește compania BASE a utilizatorului")

    # normalizează CUI
    cui = _sanitize_cui(payload.cui)
    if not (cui.isdigit() and 2 <= len(cui) <= 10):
        raise HTTPException(status_code=400, detail="CUI invalid")

    # încercăm să luăm denumirea de la ANAF (best-effort)
    today = date.today().isoformat()
    den = None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0)) as client:
            r = await client.post(
                "https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva",
                json=[{"cui": int(cui), "data": today}],
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
        if r.status_code == 200:
            raw = r.json() or {}
            found = raw.get("found") or []
            if found:
                dg = (found[0] or {}).get("date_generale") or {}
                den = (dg.get("denumire") or "").strip() or None
    except Exception:
        pass

    # upsert companie ca PRODUCER (fostul 'client')
    db.execute(
        text("""
        INSERT INTO companies(company_type, name, cui, email_contact)
        VALUES ('PRODUCER', COALESCE(:den, 'N/A'), :cui, :email)
        ON DUPLICATE KEY UPDATE
          name = COALESCE(VALUES(name), companies.name),
          email_contact = COALESCE(VALUES(email_contact), companies.email_contact)
        """),
        {"den": den, "cui": cui, "email": str(payload.email)},
    )

    row = db.execute(
        text("SELECT company_id, cui, name, company_code FROM companies WHERE cui=:cui"),
        {"cui": cui},
    ).mappings().first()
    producer_company_id = str(row["company_id"])

    # profile facturare din cache ANAF (dacă există)
    raw_cached = db.execute(
        text("SELECT raw_response FROM anaf_queries WHERE cui=:cui ORDER BY created_at DESC LIMIT 1"),
        {"cui": cui},
    ).scalar()
    if raw_cached:
        upsert_billing_profile_from_anaf(db, producer_company_id, raw_cached)

    # înlocuiește 'collaborations' cu 'relationships' PENDING (unique pe (base, partner, type))
    db.execute(
        text("""
        INSERT INTO relationships(relationship_id, base_company_id, partner_company_id, partner_type, status, created_at)
        VALUES(:id, :b, :p, 'PRODUCER', 'PENDING', NOW(6))
        ON DUPLICATE KEY UPDATE status = 'PENDING'
        """),
        {"id": str(uuid.uuid4()), "b": base_cid, "p": producer_company_id},
    )

    # invitație – păstrăm company_invitations (cu CUI) pentru compatibilitate
    token = _token()
    inv_id = str(uuid.uuid4())
    db.execute(
        text("""
        INSERT INTO company_invitations(invitation_id, base_company_id, client_company_id, cui, invited_email, token)
        VALUES(:id, :b, :p, :cui, :email, :tok)
        """),
        {"id": inv_id, "b": base_cid, "p": producer_company_id, "cui": cui, "email": str(payload.email), "tok": token},
    )

    db.execute(
        text("""INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details)
                VALUES(:uid, :cid, 'INVITE_SENT', :d)"""),
        {"uid": str(claims.get("sub")), "cid": base_cid,
         "d": json.dumps({"invitation_id": inv_id, "producer_company_id": producer_company_id,
                          "cui": cui, "email": str(payload.email)})},
    )

    db.commit()

    invite_url = f"{settings.frontend_base_url.rstrip('/')}/invite/{token}"
    return {
        "token": token,
        "invite_url": invite_url,
        "company": {
            "company_id": producer_company_id,
            "cui": row["cui"],
            "name": row["name"],
            "company_code": row["company_code"],
        }
    }

@router.get("", response_model=list[CollaborationOut])
def list_companies(claims = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    # doar BAZA listează producătorii parteneri
    if claims.get("role") != "BASE":
        raise HTTPException(status_code=403, detail="Doar BASE poate lista companiile colaboratoare")
    base_cid = str(claims.get("company_id"))

    rows = db.execute(
        text("""
        SELECT rel.partner_company_id AS producer_company_id,
               c.cui,
               c.name,
               c.company_code,
               rel.status
          FROM relationships rel
          JOIN companies c ON c.company_id = rel.partner_company_id
         WHERE rel.base_company_id = :b
           AND rel.partner_type = 'PRODUCER'
         ORDER BY c.name
        """),
        {"b": base_cid},
    ).mappings().all()

    # păstrăm cheile din CollaborationOut pentru compat cu frontendul existent
    return [{
        "client_company_id": str(r["producer_company_id"]),  # compat: aceeași cheie în UI
        "cui": r["cui"],
        "name": r["name"],
        "status": r["status"],
        "company_code": r["company_code"],
    } for r in rows]
