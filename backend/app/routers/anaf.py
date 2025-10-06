from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import date
import httpx, re, json

from app.db import get_db
from app.schemas.anaf import AnafLookupIn, AnafSummary
from app.utils.security import get_current_user_claims

from collections import defaultdict, deque
from time import time
from app.config import settings

_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)

def rate_limit_dependency(request: Request):
    ip = request.headers.get("x-forwarded-for", request.client.host)
    now = time()
    window = settings.rate_limit_window_seconds
    limit = settings.rate_limit_max_hits

    dq = _RATE_BUCKETS[ip]
    while dq and dq[0] <= now - window:
        dq.popleft()

    if len(dq) >= limit:
        raise HTTPException(status_code=429, detail="Prea multe cereri către ANAF. Încearcă mai târziu.")
    dq.append(now)

ANAF_URL = "https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva"

router = APIRouter(prefix="/anaf", tags=["anaf"])

def _sanitize_cui(raw: str) -> str:
    s = raw.strip().upper()
    s = re.sub(r"^RO", "", s)
    s = re.sub(r"\D", "", s)
    return s

@router.post("/lookup", response_model=AnafSummary)
async def anaf_lookup(
    payload: AnafLookupIn,
    request: Request,
    _: None = Depends(rate_limit_dependency),
    claims = Depends(get_current_user_claims),
    db: Session = Depends(get_db),
):
    cui = _sanitize_cui(payload.cui)
    if not cui.isdigit() or not (2 <= len(cui) <= 10):
        raise HTTPException(status_code=400, detail="CUI invalid")

    today = date.today().isoformat()
    body = [{"cui": int(cui), "data": today}]
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    raw = None
    msg = None
    code = None

    try:
        timeout = httpx.Timeout(6.0, connect=3.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(ANAF_URL, json=body, headers=headers)
        code = resp.status_code
        raw = resp.json()
    except Exception as e:
        msg = f"request_failed: {type(e).__name__}"

    # MySQL: raw_response is JSON, client_ip is VARCHAR(45); no casts
    db.execute(
        text("""
            INSERT INTO anaf_queries (cui, query_date, raw_response, result_code, message, client_ip)
            VALUES (:cui, :qd, :raw, :code, :msg, :ip)
        """),
        {
            "cui": cui,
            "qd": today,
            "raw": None if raw is None else json.dumps(raw),
            "code": code,
            "msg": msg,
            "ip": request.headers.get("x-forwarded-for", request.client.host),
        }
    )
    db.commit()

    if raw is None:
        cached = db.execute(
            text("""SELECT raw_response FROM anaf_queries
                      WHERE cui=:cui ORDER BY created_at DESC LIMIT 1"""),
            {"cui": cui}
        ).scalar()
        if cached is not None:
            if isinstance(cached, (dict, list)):
                raw = cached
            else:
                try:
                    raw = json.loads(cached)
                except Exception:
                    raw = None

    if raw is None:
        raise HTTPException(status_code=502, detail="ANAF indisponibil și fără cache")

    summary = AnafSummary(raw=raw)
    try:
        found = (raw or {}).get("found") or []
        if found:
            f = found[0]

            dg = f.get("date_generale") or f.get("dateGenerale") or {}
            summary.denumire = (dg.get("denumire") or "").strip() or None
            summary.cui = str(dg.get("cui")) if dg.get("cui") is not None else (summary.cui or cui)
            summary.address = (dg.get("adresa") or "").strip() or None
            summary.phone = (dg.get("telefon") or dg.get("phone") or "").strip() or None

            einv = (dg.get("statusRO_eFactura")
                    or dg.get("statusRo_eFactura")
                    or dg.get("status_ro_eFactura"))
            summary.e_invoice = (bool(einv) if einv is not None else None)

            sreg = (dg.get("stare_inregistrare") or "").upper()
            summary.inactive = True if ("INACTIV" in sreg or "RADIAT" in sreg) else (False if sreg else None)

            tva_scope = f.get("inregistrare_scop_Tva") or f.get("inregistrare_scop_tva") or {}
            if "scpTVA" in tva_scope:
                summary.vat_payer = bool(tva_scope.get("scpTVA"))

            tva_inc = f.get("inregistrare_RTVAI") or f.get("inregistrare_rtvai") or {}
            start = tva_inc.get("dataInceputTvaInc") or tva_inc.get("dataInceputTVAinc")
            end = tva_inc.get("dataSfarsitTvaInc") or tva_inc.get("dataSfarsitTVAinc")
            summary.vat_cash = (True if start and not end else (False if end else None))
    except Exception:
        pass

    return summary
