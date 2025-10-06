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

    if claims.get("role") != "BASE":
        raise HTTPException(status_code=403, detail="Doar utilizatorii BASE pot invita")
    base_cid = str(claims.get("company_id"))
    if not base_cid:
        raise HTTPException(status_code=400, detail="Lipsește compania BASE a utilizatorului")

    cui = _sanitize_cui(payload.cui)
    if not (cui.isdigit() and 2 <= len(cui) <= 10):
        raise HTTPException(status_code=400, detail="CUI invalid")

    today = date.today().isoformat()
    den = None
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(6.0, connect=3.0)) as client:
            r = await client.post("https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva",
                                  json=[{"cui": int(cui), "data": today}],
                                  headers={"Content-Type": "application/json", "Accept": "application/json"})
        if r.status_code == 200:
            raw = r.json()
            found = (raw or {}).get("found") or []
            if found:
                dg = found[0].get("date_generale") or {}
                den = (dg.get("denumire") or "").strip() or None
    except Exception:
        pass

    # MySQL upsert
    db.execute(
        text("""
        INSERT INTO companies(company_type, name, cui, email_contact)
        VALUES ('CLIENT', COALESCE(:den,'N/A'), :cui, :email)
        ON DUPLICATE KEY UPDATE
          name = COALESCE(VALUES(name), companies.name),
          email_contact = COALESCE(VALUES(email_contact), companies.email_contact)
        """),
        {"den": den, "cui": cui, "email": str(payload.email)}
    )

    row = db.execute(
        text("SELECT company_id, cui, name, company_code FROM companies WHERE cui=:cui"),
        {"cui": cui}
    ).mappings().first()
    client_company_id = str(row["company_id"])

    raw_cached = db.execute(
        text("SELECT raw_response FROM anaf_queries WHERE cui=:cui ORDER BY created_at DESC LIMIT 1"),
        {"cui": cui}
    ).scalar()
    if raw_cached:
        upsert_billing_profile_from_anaf(db, client_company_id, raw_cached)

    # collaborations -> PENDING (unique key on base_company_id+client_company_id)
    db.execute(
        text("""
        INSERT INTO collaborations(base_company_id, client_company_id, status)
        VALUES(:b,:c,'PENDING')
        ON DUPLICATE KEY UPDATE status='PENDING'
        """),
        {"b": base_cid, "c": client_company_id}
    )

    # invitation
    token = _token()
    inv_id = str(uuid.uuid4())
    db.execute(
        text("""
        INSERT INTO company_invitations(invitation_id, base_company_id, client_company_id, cui, invited_email, token)
        VALUES(:id,:b,:c,:cui,:email,:tok)
        """),
        {"id": inv_id, "b": base_cid, "c": client_company_id, "cui": cui, "email": str(payload.email), "tok": token}
    )

    db.execute(
        text("""INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details)
                VALUES(:uid, :cid, 'INVITE_SENT', :d)"""),
        {"uid": str(claims.get("sub")), "cid": base_cid,
         "d": json.dumps({"invitation_id": inv_id, "client_company_id": client_company_id,
                          "cui": cui, "email": str(payload.email)})}
    )

    db.commit()

    invite_url = f"{settings.frontend_base_url.rstrip('/')}/invite/{token}"
    return {
        "token": token,
        "invite_url": invite_url,
        "company": {
            "company_id": client_company_id,
            "cui": row["cui"],
            "name": row["name"],
            "company_code": row["company_code"],
        }
    }

@router.get("", response_model=list[CollaborationOut])
def list_companies(claims = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    if claims.get("role") != "BASE":
        raise HTTPException(status_code=403, detail="Doar BASE poate lista companiile colaboratoare")
    base_cid = str(claims.get("company_id"))
    rows = db.execute(
        text("""
        SELECT c.company_id AS client_company_id, c.cui, c.name, c.company_code, co.status
        FROM collaborations co
        JOIN companies c ON c.company_id = co.client_company_id
        WHERE co.base_company_id = :b
        ORDER BY c.name
        """),
        {"b": base_cid}
    ).mappings().all()

    return [{"client_company_id": str(r["client_company_id"]),
             "cui": r["cui"],
             "name": r["name"],
             "status": r["status"],
             "company_code": r["company_code"]} for r in rows]
