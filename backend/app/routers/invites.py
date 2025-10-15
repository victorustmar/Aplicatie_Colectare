# app/routers/invites.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional
from datetime import datetime, timedelta
import uuid, bcrypt, json

from app.db import get_db
from app.utils.security import create_access_token, get_current_user_claims
from app.config import settings
from app.utils.billing import upsert_billing_profile_from_anaf
from .anaf import _sanitize_cui  # reuse existing sanitizer

router = APIRouter(prefix="/invites", tags=["invites"])

# =========================
# Role typing & canonical map
# =========================

# Acceptăm și PRODUCER_2 din UI (afișezi „producator_doi”)
PartnerRoleIn = Literal["CLIENT", "RECYCLER", "PRODUCER", "PRODUCER_2", "COLLECTOR"]

def _canonical_role(r: str) -> str:
    """
    Regula UNICĂ:
      - CLIENT, PRODUCER, PRODUCER_2 -> PRODUCER
      - RECYCLER -> RECYCLER
      - COLLECTOR -> COLLECTOR
    """
    r = (r or "").upper()
    if r in ("CLIENT", "PRODUCER", "PRODUCER_2"):
        return "PRODUCER"
    if r == "RECYCLER":
        return "RECYCLER"
    if r == "COLLECTOR":
        return "COLLECTOR"
    return "PRODUCER"


# =========================
# Helpers: schema introspection
# =========================

def _table_exists(db: Session, name: str) -> bool:
    row = db.execute(
        text("""SELECT 1 FROM information_schema.tables
                WHERE table_schema = DATABASE() AND table_name = :t LIMIT 1"""),
        {"t": name},
    ).scalar()
    return bool(row)

def _column_exists(db: Session, table: str, col: str) -> bool:
    row = db.execute(
        text("""SELECT 1 FROM information_schema.columns
                WHERE table_schema = DATABASE()
                  AND table_name = :t AND column_name = :c LIMIT 1"""),
        {"t": table, "c": col},
    ).scalar()
    return bool(row)

def _invite_table(db: Session) -> str:
    # Prefer the new table if present
    return "invites" if _table_exists(db, "invites") else "company_invitations"

def _has_target_role(db: Session, table: str) -> bool:
    return _column_exists(db, table, "target_role")

def _has_cui_col(db: Session, table: str) -> bool:
    return _column_exists(db, table, "cui")


# =========================
# Schemas
# =========================

class CreateInviteIn(BaseModel):
    email: EmailStr
    target_role: PartnerRoleIn
    cui: Optional[str] = None
    company_name: Optional[str] = None
    expires_in_days: int = Field(default=14, ge=1, le=90)

class InviteOut(BaseModel):
    token: str
    invite_url: str
    # Returnăm mereu rolul CANONIC
    target_role: Literal["PRODUCER", "COLLECTOR", "RECYCLER"]
    company: dict

class AcceptInviteIn(BaseModel):
    token: str
    password: str
    full_name: str
    phone: Optional[str] = Field(default=None, max_length=50)


# =========================
# Endpoints
# =========================

@router.post("", response_model=InviteOut)
def create_invite(
    payload: CreateInviteIn,
    claims = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    # Doar BAZĂ
    if claims.get("role") != "BASE":
        raise HTTPException(403, "Doar utilizatorii de tip BAZĂ pot trimite invitații")

    base_company_id = claims.get("company_id")
    if not base_company_id:
        raise HTTPException(422, "Lipsește compania utilizatorului")

    canonical = _canonical_role(payload.target_role)

    # Normalize CUI
    cui_norm: Optional[str] = None
    if payload.cui:
        c = _sanitize_cui(payload.cui)
        cui_norm = c if c else None

    # 1) find/create partner company
    target = None
    if cui_norm:
        target = db.execute(
            text("SELECT company_id, cui, name, company_code FROM companies WHERE cui = :c"),
            {"c": cui_norm},
        ).mappings().first()

    if not target:
        comp_id = str(uuid.uuid4())
        db.execute(
            text("""
                INSERT INTO companies (company_id, company_type, cui, name, email_contact)
                VALUES (:id, :ctype, COALESCE(:cui,''), :name, :email)
            """),
            {
                "id": comp_id,
                "ctype": canonical,  # PRODUCER / RECYCLER / COLLECTOR
                "cui": cui_norm,
                "name": (payload.company_name or "").strip() or "Companie",
                "email": str(payload.email),
            },
        )
        db.commit()
        target = db.execute(
            text("SELECT company_id, cui, name, company_code FROM companies WHERE company_id = :id"),
            {"id": comp_id},
        ).mappings().first()

    if not target:
        raise HTTPException(500, "Nu am putut crea/obține compania partener")

    partner_company_id = str(target["company_id"])

    # 1.b) Billing profile din ANAF cache sau minim
    if cui_norm:
        raw_cached = db.execute(
            text("SELECT raw_response FROM anaf_queries WHERE cui = :cui ORDER BY created_at DESC LIMIT 1"),
            {"cui": cui_norm},
        ).scalar()
        if raw_cached:
            upsert_billing_profile_from_anaf(db, partner_company_id, raw_cached)
        else:
            db.execute(
                text("""
                    INSERT INTO company_billing_profiles (
                        company_id, legal_name, cui, country, source, updated_from_anaf_at
                    )
                    SELECT c.company_id,
                           COALESCE(NULLIF(TRIM(c.name), ''), 'Companie'),
                           COALESCE(c.cui, ''), 'RO', 'USER', NOW(6)
                      FROM companies c
                      LEFT JOIN company_billing_profiles p ON p.company_id = c.company_id
                     WHERE c.company_id = :cid AND p.company_id IS NULL
                """),
                {"cid": partner_company_id},
            )
    else:
        db.execute(
            text("""
                INSERT INTO company_billing_profiles (
                    company_id, legal_name, cui, country, source, updated_from_anaf_at
                )
                SELECT c.company_id,
                       COALESCE(NULLIF(TRIM(c.name), ''), 'Companie'),
                       COALESCE(c.cui, ''), 'RO', 'USER', NOW(6)
                  FROM companies c
                  LEFT JOIN company_billing_profiles p ON p.company_id = c.company_id
                 WHERE c.company_id = :cid AND p.company_id IS NULL
            """),
            {"cid": partner_company_id},
        )

    token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=payload.expires_in_days)  # naive UTC (match NOW(6))

    tbl = _invite_table(db)
    has_role = _has_target_role(db, tbl)
    has_cui = _has_cui_col(db, tbl)

    # 2) write invitation (mereu rol CANONIC)
    if tbl == "invites":
        if has_role:
            if has_cui:
                db.execute(
                    text("""
                        INSERT INTO invites(
                            token, base_company_id, client_company_id, invited_email,
                            target_role, cui, status, created_at, expires_at
                        )
                        VALUES (:t, :b, :c, :e, :r, :cui, 'PENDING', NOW(6), :exp)
                    """),
                    {"t": token, "b": base_company_id, "c": partner_company_id, "e": str(payload.email),
                     "r": canonical, "cui": cui_norm, "exp": expires_at},
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO invites(
                            token, base_company_id, client_company_id, invited_email,
                            target_role, status, created_at, expires_at
                        )
                        VALUES (:t, :b, :c, :e, :r, 'PENDING', NOW(6), :exp)
                    """),
                    {"t": token, "b": base_company_id, "c": partner_company_id, "e": str(payload.email),
                     "r": canonical, "exp": expires_at},
                )
        else:
            if has_cui:
                db.execute(
                    text("""
                        INSERT INTO invites(
                            token, base_company_id, client_company_id, invited_email,
                            cui, status, created_at, expires_at
                        )
                        VALUES (:t, :b, :c, :e, :cui, 'PENDING', NOW(6), :exp)
                    """),
                    {"t": token, "b": base_company_id, "c": partner_company_id, "e": str(payload.email),
                     "cui": cui_norm, "exp": expires_at},
                )
            else:
                db.execute(
                    text("""
                        INSERT INTO invites(
                            token, base_company_id, client_company_id, invited_email,
                            status, created_at, expires_at
                        )
                        VALUES (:t, :b, :c, :e, 'PENDING', NOW(6), :exp)
                    """),
                    {"t": token, "b": base_company_id, "c": partner_company_id, "e": str(payload.email),
                     "exp": expires_at},
                )
    else:
        # legacy: company_invitations
        if has_role and has_cui:
            db.execute(
                text("""
                    INSERT INTO company_invitations(
                        invitation_id, token, base_company_id, client_company_id,
                        invited_email, target_role, cui, created_at, expires_at
                    )
                    VALUES (:id, :t, :b, :c, :e, :r, :cui, NOW(6), :exp)
                """),
                {"id": str(uuid.uuid4()), "t": token, "b": base_company_id, "c": partner_company_id,
                 "e": str(payload.email), "r": canonical, "cui": cui_norm or "", "exp": expires_at},
            )
        elif has_role and not has_cui:
            db.execute(
                text("""
                    INSERT INTO company_invitations(
                        invitation_id, token, base_company_id, client_company_id,
                        invited_email, target_role, created_at, expires_at
                    )
                    VALUES (:id, :t, :b, :c, :e, :r, NOW(6), :exp)
                """),
                {"id": str(uuid.uuid4()), "t": token, "b": base_company_id, "c": partner_company_id,
                 "e": str(payload.email), "r": canonical, "exp": expires_at},
            )
        elif not has_role and has_cui:
            db.execute(
                text("""
                    INSERT INTO company_invitations(
                        invitation_id, token, base_company_id, client_company_id,
                        invited_email, cui, created_at, expires_at
                    )
                    VALUES (:id, :t, :b, :c, :e, :cui, NOW(6), :exp)
                """),
                {"id": str(uuid.uuid4()), "t": token, "b": base_company_id, "c": partner_company_id,
                 "e": str(payload.email), "cui": cui_norm or "", "exp": expires_at},
            )
        else:
            db.execute(
                text("""
                    INSERT INTO company_invitations(
                        invitation_id, token, base_company_id, client_company_id,
                        invited_email, created_at, expires_at
                    )
                    VALUES (:id, :t, :b, :c, :e, NOW(6), :exp)
                """),
                {"id": str(uuid.uuid4()), "t": token, "b": base_company_id, "c": partner_company_id,
                 "e": str(payload.email), "exp": expires_at},
            )

    db.commit()

    return {
        "token": token,
        "invite_url": f"/invite/{token}",
        "target_role": canonical,
        "company": {
            "company_id": partner_company_id,
            "cui": target.get("cui"),
            "name": target.get("name"),
            "company_code": target.get("company_code"),
        },
    }


@router.post("/accept")
def accept_invite(payload: AcceptInviteIn, db: Session = Depends(get_db)):
    tbl = _invite_table(db)
    has_role = _has_target_role(db, tbl)

    # 1) citește invitația
    if tbl == "invites":
        inv = db.execute(
            text("""
                SELECT token, base_company_id, client_company_id, invited_email,
                       target_role AS target_role,
                       expires_at, accepted_at
                  FROM invites
                 WHERE token = :t
            """),
            {"t": payload.token},
        ).mappings().first()
    else:
        inv = db.execute(
            text("""
                SELECT token, base_company_id, client_company_id, invited_email,
                       {role_expr} AS target_role,
                       expires_at, accepted_at
                  FROM company_invitations
                 WHERE token = :t
            """.format(role_expr="target_role" if has_role else "'CLIENT'")),
            {"t": payload.token},
        ).mappings().first()

    if not inv:
        raise HTTPException(404, "Invitația nu există")
    if inv["accepted_at"] is not None:
        raise HTTPException(409, "Invitația a fost deja acceptată")

    # Compară exp la naive UTC (DB NOW(6) = naive UTC)
    now_utc_naive = datetime.utcnow()
    exp = inv["expires_at"]
    if isinstance(exp, datetime) and getattr(exp, "tzinfo", None) is not None:
        exp = exp.replace(tzinfo=None)
    if exp and exp < now_utc_naive:
        raise HTTPException(410, "Invitația a expirat")

    email = inv["invited_email"]
    base_company_id = str(inv["base_company_id"])
    partner_company_id = str(inv["client_company_id"])

    raw_role = str(inv.get("target_role") or "CLIENT")
    target_role = _canonical_role(raw_role)  # PRODUCER / RECYCLER / COLLECTOR

    # 2) email trebuie să fie liber
    exists = db.execute(text("SELECT 1 FROM users WHERE email=:e LIMIT 1"), {"e": email}).scalar()
    if exists:
        raise HTTPException(409, "Există deja un utilizator cu acest email")

    # 3) creează user cu rolul canonic
    user_id = str(uuid.uuid4())
    pw_hash = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    db.execute(
        text("""
            INSERT INTO users(user_id, email, password_hash, role, full_name, company_id, is_active)
            VALUES (:id, :e, :ph, :role, :name, :cid, 1)
        """),
        {"id": user_id, "e": email, "ph": pw_hash, "role": target_role,
         "name": payload.full_name, "cid": partner_company_id},
    )

    # 4) marchează invitația ca acceptată
    if tbl == "invites":
        db.execute(text("UPDATE invites SET accepted_at = NOW(6) WHERE token = :t"), {"t": payload.token})
    else:
        db.execute(text("UPDATE company_invitations SET accepted_at = NOW(6) WHERE token = :t"), {"t": payload.token})

    # 5) legături
    if target_role == "PRODUCER":
        # compat: producătorii în 'collaborations'
        db.execute(
            text("""
                INSERT INTO collaborations (base_company_id, client_company_id, status, created_at)
                VALUES (:b, :c, 'ACTIVE', NOW(6))
                ON DUPLICATE KEY UPDATE status = 'ACTIVE'
            """),
            {"b": base_company_id, "c": partner_company_id},
        )
    else:
        # RECYCLER / COLLECTOR în 'relationships'
        existing = db.execute(
            text("""
                SELECT relationship_id, status
                  FROM relationships
                 WHERE base_company_id=:b AND partner_company_id=:p AND partner_type=:t
            """),
            {"b": base_company_id, "p": partner_company_id, "t": target_role},
        ).mappings().first()
        if existing:
            if existing["status"] != "ACTIVE":
                db.execute(
                    text("UPDATE relationships SET status='ACTIVE' WHERE relationship_id=:id"),
                    {"id": str(existing["relationship_id"])},
                )
        else:
            db.execute(
                text("""
                    INSERT INTO relationships(
                        relationship_id, base_company_id, partner_company_id, partner_type, status, created_at
                    )
                    VALUES(:id, :b, :p, :t, 'ACTIVE', NOW(6))
                """),
                {"id": str(uuid.uuid4()), "b": base_company_id, "p": partner_company_id, "t": target_role},
            )

    # 6) completează/actualizează telefonul pe profilul de facturare (fără a șterge date ANAF)
    phone = (payload.phone or "").strip() or None
    db.execute(
        text("""
            INSERT INTO company_billing_profiles (company_id, legal_name, cui, country, source, updated_from_anaf_at)
            SELECT c.company_id,
                   COALESCE(NULLIF(TRIM(c.name), ''), 'Companie'),
                   COALESCE(c.cui, ''),
                   'RO', 'USER', NOW(6)
              FROM companies c
              LEFT JOIN company_billing_profiles p ON p.company_id = c.company_id
             WHERE c.company_id = :cid AND p.company_id IS NULL
        """),
        {"cid": partner_company_id},
    )
    db.execute(
        text("""
            UPDATE company_billing_profiles
               SET phone_billing = :p, updated_from_anaf_at = NOW(6), source=COALESCE(source,'USER')
             WHERE company_id = :cid
        """),
        {"cid": partner_company_id, "p": phone},
    )

    # 7) token + audit
    claims = {"sub": user_id, "role": target_role, "company_id": partner_company_id}
    token, _ = create_access_token(settings.jwt_secret, claims)

    db.execute(
        text("""INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details)
                VALUES (:uid, :cid, 'INVITE_ACCEPTED', :d)"""),
        {"uid": user_id, "cid": partner_company_id,
         "d": json.dumps({"token": payload.token, "target_role": target_role})},
    )

    db.commit()

    company_name = db.execute(
        text("SELECT name FROM companies WHERE company_id=:cid"), {"cid": partner_company_id}
    ).scalar()

    return {
        "access_token": token,
        "user": {
            "user_id": user_id,
            "role": target_role,
            "company_id": partner_company_id,
            "full_name": payload.full_name,
            "company_name": company_name,
        },
    }
