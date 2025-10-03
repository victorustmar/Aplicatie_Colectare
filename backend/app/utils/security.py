import uuid, datetime as dt
import jwt
from typing import Any, Dict

from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import settings
from app.db import get_db
from .typing import StrDict

JWT_ALG = "HS256"
ACCESS_TTL_MIN = 30

def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)

def create_access_token(secret: str, claims: Dict[str, Any], ttl_min: int = ACCESS_TTL_MIN, jti: str | None = None) -> tuple[str, str]:
    """Returnează (token, jti)."""
    jti = jti or str(uuid.uuid4())
    payload = {
        "jti": jti,
        "iat": int(now_utc().timestamp()),
        "exp": int((now_utc() + dt.timedelta(minutes=ttl_min)).timestamp()),
        "iss": "app-suite",
        "aud": "app-suite",
        **claims,
    }
    token = jwt.encode(payload, secret, algorithm=JWT_ALG)
    return token, jti

def decode_token(secret: str, token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, secret, algorithms=[JWT_ALG], audience="app-suite")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirat")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalid")

_security = HTTPBearer(auto_error=True)

async def get_current_user_claims(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    db: Session = Depends(get_db),
) -> StrDict:
    token = credentials.credentials
    claims = decode_token(settings.jwt_secret, token)

    jti = claims.get("jti")
    uid = claims.get("sub")
    if not jti or not uid:
        raise HTTPException(status_code=401, detail="Sesiune invalidă")

    row = db.execute(
        text("SELECT revoked_at FROM user_sessions WHERE jti = :jti AND user_id = :uid"),
        {"jti": jti, "uid": uid}
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=401, detail="Sesiune inexistentă")
    if row["revoked_at"] is not None:
        raise HTTPException(status_code=401, detail="Sesiune revocată")

    request.state.jwt = claims
    return claims
