from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import bcrypt, json

from app.db import get_db
from app.schemas.invites import AcceptInviteIn
from app.schemas.auth import LoginOut, UserOut  # pentru tipuri răspuns
from app.utils.security import create_access_token
from app.config import settings

router = APIRouter(prefix="/invites", tags=["invites"])

@router.post("/accept", response_model=LoginOut)
def accept_invite(payload: AcceptInviteIn, request: Request, db: Session = Depends(get_db)):
    # 1) găsește invitația
    inv = db.execute(
        text("""SELECT invitation_id, base_company_id, client_company_id, invited_email, expires_at, accepted_at
                FROM company_invitations WHERE token=:t"""),
        {"t": payload.token}
    ).mappings().first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitație invalidă")
    if inv["accepted_at"]:
        raise HTTPException(status_code=400, detail="Invitație deja acceptată")
    if inv["expires_at"] and inv["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invitație expirată")

    cid = inv["client_company_id"]
    if not cid:
        raise HTTPException(status_code=500, detail="Compania nu a fost creată corect")

    # 2) verifică dacă emailul există deja
    ex = db.execute(
        text("SELECT user_id, company_id FROM users WHERE email=:em"),
        {"em": inv["invited_email"]}
    ).mappings().first()
    if ex and ex["company_id"] != cid:
        raise HTTPException(status_code=409, detail="Acest email este deja folosit la o altă companie")

    # 3) creează user (sau folosește existentul din aceeași companie)
    if ex and ex["company_id"] == cid:
        user_id = ex["user_id"]
    else:
        pwd_hash = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user_id = db.execute(
            text("""INSERT INTO users(company_id, role, full_name, email, password_hash, is_active)
                    VALUES(:cid, 'CLIENT', :fn, :em, :ph, true)
                    RETURNING user_id"""),
            {"cid": cid, "fn": payload.full_name.strip(), "em": inv["invited_email"], "ph": pwd_hash}
        ).scalar()

    # 4) marchează invitația & activează colaborarea
    db.execute(text("UPDATE company_invitations SET accepted_at = now() WHERE invitation_id=:id"),
               {"id": inv["invitation_id"]})
    db.execute(text("UPDATE collaborations SET status='ACTIVE' WHERE client_company_id=:cid"),
               {"cid": cid})

    # 5) login instant – token + sesiune + audit
    claims = {"sub": str(user_id), "role": "CLIENT", "company_id": str(cid)}
    token, jti = create_access_token(settings.jwt_secret, claims)

    db.execute(
        text("""INSERT INTO user_sessions (user_id, ip_address, user_agent, jti)
                VALUES (:uid, CAST(:ip AS INET), :ua, :jti)"""),
        {"uid": user_id,
         "ip": request.headers.get("x-forwarded-for", request.client.host),
         "ua": request.headers.get("user-agent", ""),
         "jti": jti}
    )
    db.execute(
        text("""INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details, ip_address, user_agent)
                VALUES (:uid, :cid, 'INVITE_ACCEPTED', CAST(:d AS JSONB), CAST(:ip AS INET), :ua)"""),
        {"uid": user_id, "cid": cid,
         "d": json.dumps({"invitation_id": str(inv["invitation_id"])}),
         "ip": request.headers.get("x-forwarded-for", request.client.host),
         "ua": request.headers.get("user-agent", "")}
    )

    db.commit()

    # opțional: numele companiei pentru UI
    cname = db.execute(text("SELECT name FROM companies WHERE company_id=:cid"), {"cid": cid}).scalar()

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "user_id": str(user_id),
            "role": "CLIENT",
            "company_id": str(cid),
            "full_name": payload.full_name,
            "company_name": cname
        }
    }
