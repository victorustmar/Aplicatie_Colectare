from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
import bcrypt, json
from app.db import get_db
from app.config import settings
from app.schemas.auth import LoginIn, LoginOut, UserOut
from app.utils.security import create_access_token, get_current_user_claims

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=LoginOut)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    row = db.execute(
        text("""SELECT user_id, company_id, role, full_name, email, password_hash, is_active
                FROM users WHERE email = :email"""),
        {"email": payload.email}
    ).mappings().first()

    if not row or not row["is_active"]:
        raise HTTPException(status_code=401, detail="Email sau parolă greșite")

    if not bcrypt.checkpw(payload.password.encode("utf-8"), row["password_hash"].encode("utf-8")):
        raise HTTPException(status_code=401, detail="Email sau parolă greșite")

    claims = {
        "sub": str(row["user_id"]),
        "role": row["role"],
        "company_id": str(row["company_id"]) if row["company_id"] else None,
    }
    token, jti = create_access_token(settings.jwt_secret, claims)

    # session + audit (folosește CAST pentru INET/JSONB)
    db.execute(
        text("""INSERT INTO user_sessions (user_id, ip_address, user_agent, jti)
                 VALUES (:uid, CAST(:ip AS INET), :ua, :jti)"""),
        {
            "uid": row["user_id"],
            "ip": request.headers.get("x-forwarded-for", request.client.host),
            "ua": request.headers.get("user-agent", ""),
            "jti": jti,
        }
    )
    db.execute(
        text("""INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details, ip_address, user_agent)
                 VALUES (:uid, :cid, 'LOGIN', CAST(:details AS JSONB), CAST(:ip AS INET), :ua)"""),
        {
            "uid": row["user_id"],
            "cid": row["company_id"],
            "details": json.dumps({"success": True, "jti": jti}),
            "ip": request.headers.get("x-forwarded-for", request.client.host),
            "ua": request.headers.get("user-agent", ""),
        }
    )
    db.commit()

    company_name = None
    if row["company_id"]:
        cn = db.execute(
            text("SELECT name FROM companies WHERE company_id = :cid"), {"cid": row["company_id"]}
        ).scalar()
        company_name = cn

    return {
        "access_token": token,
        "user": {
            "user_id": str(row["user_id"]),
            "role": row["role"],
            "company_id": str(row["company_id"]) if row["company_id"] else None,
            "full_name": row["full_name"],
            "company_name": company_name
        }
    }

@router.get("/me", response_model=UserOut)
def me(claims=Depends(get_current_user_claims), db: Session = Depends(get_db)):
    uid = claims.get("sub")
    row = db.execute(
        text("""SELECT u.user_id, u.role, u.company_id, u.full_name, c.name AS company_name
                 FROM users u
                 LEFT JOIN companies c ON c.company_id = u.company_id
                 WHERE u.user_id = :uid"""),
        {"uid": uid}
    ).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Utilizator inexistent")

    return {
        "user_id": str(row["user_id"]),
        "role": row["role"],
        "company_id": str(row["company_id"]) if row["company_id"] else None,
        "full_name": row["full_name"],
        "company_name": row["company_name"],
    }

@router.post("/logout")
def logout(request: Request, claims=Depends(get_current_user_claims), db: Session = Depends(get_db)):
    uid = claims.get("sub")
    jti = claims.get("jti")
    # marchează sesiunea ca revocată
    res = db.execute(
        text("""UPDATE user_sessions
                SET revoked_at = now()
                WHERE user_id = :uid AND jti = :jti AND revoked_at IS NULL"""),
        {"uid": uid, "jti": jti}
    )
    # audit
    db.execute(
        text("""INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details, ip_address, user_agent)
                 VALUES (:uid, NULL, 'LOGOUT', CAST(:details AS JSONB), CAST(:ip AS INET), :ua)"""),
        {
            "uid": uid,
            "details": json.dumps({"revoked": bool(res.rowcount), "jti": jti}),
            "ip": request.headers.get("x-forwarded-for", request.client.host),
            "ua": request.headers.get("user-agent", ""),
        }
    )
    db.commit()
    return {"ok": True}
