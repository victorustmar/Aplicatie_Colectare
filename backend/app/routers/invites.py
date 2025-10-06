from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import bcrypt, json, uuid
from pydantic import BaseModel, Field

from app.db import get_db
from app.utils.security import create_access_token
from app.config import settings

router = APIRouter(prefix="/invites", tags=["invites"])
# @router.post("/accept", response_model=LoginOut)
# def accept_invite(payload: AcceptInviteIn, request: Request, db: Session = Depends(get_db)):
#     inv = db.execute(
#         text("""SELECT invitation_id, base_company_id, client_company_id, invited_email, expires_at, accepted_at
#                 FROM company_invitations WHERE token=:t"""),
#         {"t": payload.token}
#     ).mappings().first()
#     if not inv:
#         raise HTTPException(status_code=404, detail="Invitație invalidă")
#     if inv["accepted_at"]:
#         raise HTTPException(status_code=400, detail="Invitație deja acceptată")
#     if inv["expires_at"] and inv["expires_at"] < datetime.now(timezone.utc):
#         raise HTTPException(status_code=400, detail="Invitație expirată")
#
#     cid = str(inv["client_company_id"])
#     if not cid:
#         raise HTTPException(status_code=500, detail="Compania nu a fost creată corect")
#
#     ex = db.execute(
#         text("SELECT user_id, company_id FROM users WHERE email=:em"),
#         {"em": inv["invited_email"]}
#     ).mappings().first()
#     if ex and str(ex["company_id"]) != cid:
#         raise HTTPException(status_code=409, detail="Acest email este deja folosit la o altă companie")
#
#     if ex and str(ex["company_id"]) == cid:
#         user_id = str(ex["user_id"])
#     else:
#         pwd_hash = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
#         user_id = str(uuid.uuid4())
#         db.execute(
#             text("""INSERT INTO users(user_id, company_id, role, full_name, email, password_hash, is_active)
#                     VALUES(:uid, :cid, 'CLIENT', :fn, :em, :ph, true)"""),
#             {"uid": user_id, "cid": cid, "fn": payload.full_name.strip(), "em": inv["invited_email"], "ph": pwd_hash}
#         )
#
#     db.execute(text("UPDATE company_invitations SET accepted_at = NOW() WHERE invitation_id=:id"),
#                {"id": str(inv["invitation_id"])})
#     db.execute(text("UPDATE collaborations SET status='ACTIVE' WHERE client_company_id=:cid"),
#                {"cid": cid})
#
#     claims = {"sub": user_id, "role": "CLIENT", "company_id": cid}
#     token, jti = create_access_token(settings.jwt_secret, claims)
#
#     db.execute(
#         text("""INSERT INTO user_sessions (user_id, ip_address, user_agent, jti)
#                 VALUES (:uid, :ip, :ua, :jti)"""),
#         {"uid": user_id,
#          "ip": request.headers.get("x-forwarded-for", request.client.host),
#          "ua": request.headers.get("user-agent", ""),
#          "jti": jti}
#     )
#     db.execute(
#         text("""INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details, ip_address, user_agent)
#                 VALUES (:uid, :cid, 'INVITE_ACCEPTED', :d, :ip, :ua)"""),
#         {"uid": user_id, "cid": cid,
#          "d": json.dumps({"invitation_id": str(inv["invitation_id"])}),
#          "ip": request.headers.get("x-forwarded-for", request.client.host),
#          "ua": request.headers.get("user-agent", "")}
#     )
#
#     db.commit()
#
#     cname = db.execute(text("SELECT name FROM companies WHERE company_id=:cid"), {"cid": cid}).scalar()
#
#     return {
#         "access_token": token,
#         "token_type": "bearer",
#         "user": {
#             "user_id": user_id,
#             "role": "CLIENT",
#             "company_id": cid,
#             "full_name": payload.full_name,
#             "company_name": cname
#         }
#     }


# We define the payload here (we're not importing it) to include the phone field.
class AcceptInviteIn(BaseModel):
    token: str
    password: str
    full_name: str
    phone: str | None = Field(default=None, max_length=50)


@router.post("/accept")
def accept_invite(payload: AcceptInviteIn, db: Session = Depends(get_db)):
    # 1) Find a valid invite
    inv = db.execute(
        text("""
            SELECT invitation_id, base_company_id, client_company_id, invited_email,
                   expires_at, accepted_at
              FROM company_invitations
             WHERE token = :t
        """),
        {"t": payload.token},
    ).mappings().first()

    if not inv:
        raise HTTPException(404, "Invitația nu există")
    if inv["accepted_at"] is not None:
        raise HTTPException(409, "Invitația a fost deja acceptată")
    if inv["expires_at"] is not None and inv["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(410, "Invitația a expirat")

    email = inv["invited_email"]
    base_company_id = str(inv["base_company_id"])
    client_company_id = str(inv["client_company_id"])

    # 2) Ensure the email is not already used
    exists = db.execute(text("SELECT 1 FROM users WHERE email=:e LIMIT 1"), {"e": email}).scalar()
    if exists:
        raise HTTPException(409, "Există deja un utilizator cu acest email")

    # 3) Create CLIENT user
    user_id = str(uuid.uuid4())
    pw_hash = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    db.execute(
        text("""
            INSERT INTO users(user_id, email, password_hash, role, full_name, company_id, is_active)
            VALUES (:id, :e, :ph, 'CLIENT', :name, :cid, 1)
        """),
        {"id": user_id, "e": email, "ph": pw_hash, "name": payload.full_name, "cid": client_company_id},
    )

    # 4) Mark invite accepted (by token is fine; invitation_id works too)
    db.execute(
        text("UPDATE company_invitations SET accepted_at = NOW(6) WHERE token = :t"),
        {"t": payload.token},
    )

    # 5) Ensure collaboration is ACTIVE (insert or update)
    # Requires a UNIQUE KEY on (base_company_id, client_company_id)
    db.execute(
        text("""
            INSERT INTO collaborations (base_company_id, client_company_id, status, created_at)
            VALUES (:b, :c, 'ACTIVE', NOW(6))
            ON DUPLICATE KEY UPDATE status = 'ACTIVE'
        """),
        {"b": base_company_id, "c": client_company_id},
    )

    # 6) Ensure a minimal billing profile exists, then ALWAYS overwrite phone
    phone = (payload.phone or "").strip() or None

    # Create the row if missing (fill NOT NULL columns)
    db.execute(
        text("""
            INSERT INTO company_billing_profiles (
                company_id, legal_name, cui, country, source, updated_from_anaf_at
            )
            SELECT c.company_id,
                   COALESCE(NULLIF(TRIM(c.name), ''), 'Client'),
                   COALESCE(c.cui, ''),
                   'RO',
                   'USER',
                   NOW(6)
              FROM companies c
              LEFT JOIN company_billing_profiles p ON p.company_id = c.company_id
             WHERE c.company_id = :cid
               AND p.company_id IS NULL
        """),
        {"cid": client_company_id},
    )

    # Overwrite phone every time (even with NULL if not provided)
    db.execute(
        text("""
            UPDATE company_billing_profiles
               SET phone_billing        = :p,
                   updated_from_anaf_at = NOW(6),
                   source               = 'USER'
             WHERE company_id = :cid
        """),
        {"cid": client_company_id, "p": phone},
    )

    # 7) Issue token and audit
    claims = {"sub": user_id, "role": "CLIENT", "company_id": client_company_id}
    token, _ = create_access_token(settings.jwt_secret, claims)

    db.execute(
        text("""INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details)
                VALUES (:uid, :cid, 'INVITE_ACCEPTED', :d)"""),
        {"uid": user_id, "cid": client_company_id, "d": json.dumps({"email": email, "phone": phone})},
    )

    db.commit()

    company_name = db.execute(
        text("SELECT name FROM companies WHERE company_id=:cid"), {"cid": client_company_id}
    ).scalar()

    return {
        "access_token": token,
        "user": {
            "user_id": user_id,
            "role": "CLIENT",
            "company_id": client_company_id,
            "full_name": payload.full_name,
            "company_name": company_name,
        },
    }