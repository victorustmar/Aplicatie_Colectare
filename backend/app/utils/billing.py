from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import json

def extract_profile_from_anaf_raw(raw) -> dict:
    """Accept MySQL JSON (str/bytes) or dict and return a dict."""
    if raw is None:
        return {}

    # MySQL JSON may arrive as bytes/str — decode/parse
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = raw.decode("utf-8", "ignore")
        except Exception:
            return {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return {}

    # now assume dict
    found = (raw or {}).get("found") or []
    if not found:
        return {}

    f = found[0]
    dg = f.get("date_generale") or {}

    legal_name = (dg.get("denumire") or "").strip() or None
    cui = str(dg.get("cui") or f.get("cui") or "").strip()
    address = (dg.get("adresa") or "").strip() or None
    reg = (dg.get("nrRegCom") or dg.get("nrRegComert") or "").strip() or None
    phone = (dg.get("telefon") or "").strip() or None

    vat_payer = bool(f.get("scpTVA")) if "scpTVA" in f else None
    vat_cash = bool(f.get("scpTVAincas")) if "scpTVAincas" in f else None
    e_invoice = bool(f.get("stare_inregistrare_spv")) if "stare_inregistrare_spv" in f else None

    return {
        "legal_name": legal_name,
        "cui": cui,
        "reg_com": reg,
        "address_line": address,
        "phone_billing": phone,
        "vat_payer": vat_payer,
        "vat_cash": vat_cash,
        "e_invoice": e_invoice,
    }
def upsert_billing_profile_from_anaf(db: Session, company_id: str, raw: dict | str | bytes) -> None:
    from .billing import extract_profile_from_anaf_raw  # if in same module, remove this import

    data = extract_profile_from_anaf_raw(raw)
    if not data:
        return

    # ensure CUI and some defaults
    if not data.get("cui"):
        cui = db.execute(text("SELECT cui FROM companies WHERE company_id=:cid"), {"cid": company_id}).scalar()
        if cui:
            data["cui"] = cui
    data.setdefault("country", "RO")
    data["updated_from_anaf_at"] = datetime.utcnow()
    data["source"] = "ANAF"

    # MySQL ON DUPLICATE KEY UPDATE must qualify target table columns
    db.execute(
        text("""
            INSERT INTO company_billing_profiles (
                company_id, legal_name, cui, reg_com, address_line, city, county, postal_code,
                country, bank_name, iban, email_billing, phone_billing, vat_payer, vat_cash,
                e_invoice, updated_from_anaf_at, source
            )
            VALUES (
                :cid, :legal_name, :cui, :reg_com, :address_line, NULL, NULL, NULL,
                :country, NULL, NULL, NULL, :phone_billing, :vat_payer, :vat_cash,
                :e_invoice, :updated_from_anaf_at, :source
            )
            AS new
            ON DUPLICATE KEY UPDATE
                company_billing_profiles.legal_name           = new.legal_name,
                company_billing_profiles.cui                  = new.cui,
                company_billing_profiles.reg_com              = COALESCE(new.reg_com, company_billing_profiles.reg_com),
                company_billing_profiles.address_line         = COALESCE(new.address_line, company_billing_profiles.address_line),
                company_billing_profiles.phone_billing        = COALESCE(new.phone_billing, company_billing_profiles.phone_billing),
                company_billing_profiles.vat_payer            = new.vat_payer,
                company_billing_profiles.vat_cash             = new.vat_cash,
                company_billing_profiles.e_invoice            = new.e_invoice,
                company_billing_profiles.updated_from_anaf_at = new.updated_from_anaf_at,
                company_billing_profiles.source               = 'ANAF'
        """),
        {"cid": company_id, **data}
    )

def billing_ready(db: Session, base_cid: str, client_cid: str) -> tuple[bool, str]:
    # baza: profil + settings
    base_p = db.execute(
        text("SELECT 1 FROM company_billing_profiles WHERE company_id = :cid"),
        {"cid": base_cid},
    ).scalar()
    base_s = db.execute(
        text("SELECT 1 FROM company_invoice_settings WHERE base_company_id = :cid"),
        {"cid": base_cid},
    ).scalar()
    # client: profil
    client_p = db.execute(
        text("SELECT 1 FROM company_billing_profiles WHERE company_id = :cid"),
        {"cid": client_cid},
    ).scalar()

    if not base_p:
        return False, "Completează profilul de facturare al BAZEI"
    if not base_s:
        return False, "Configurează setările de facturare (serie/număr) pentru BAZĂ"
    if not client_p:
        return False, "Completează profilul de facturare al CLIENTULUI"
    return True, ""
