from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

def extract_profile_from_anaf_raw(raw: dict) -> dict:
    """Scoate câmpurile relevante din răspunsul ANAF (v9)."""
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

def upsert_billing_profile_from_anaf(db: Session, company_id: str, raw: dict) -> None:
    data = extract_profile_from_anaf_raw(raw)
    if not data:
        return
    data["updated_from_anaf_at"] = datetime.utcnow().isoformat()
    data["source"] = "ANAF"

    # completează cu valori minime dacă lipsesc
    # (legal_name și cui sunt importante; dacă lipsesc, nu inserăm)
    if not data.get("legal_name"):
        return
    if not data.get("cui"):
        # încearcă cui din companies
        cui = db.execute(text("SELECT cui FROM companies WHERE company_id=:cid"), {"cid": company_id}).scalar()
        if cui:
            data["cui"] = cui

    data.setdefault("country", "RO")

    # folosește un datetime real; nu mai facem cast în SQL
    data["updated_from_anaf_at"] = datetime.utcnow()
    data["source"] = "ANAF"

    # upsert
    db.execute(
        text("""
            INSERT INTO company_billing_profiles(
                company_id, legal_name, cui, reg_com, address_line, city, county, postal_code,
                country, bank_name, iban, email_billing, phone_billing, vat_payer, vat_cash,
                e_invoice, updated_from_anaf_at, source
            )
            VALUES(
                :cid, :legal_name, :cui, :reg_com, :address_line, NULL, NULL, NULL,
                :country, NULL, NULL, NULL, :phone_billing, :vat_payer, :vat_cash,
                :e_invoice, :updated_from_anaf_at, :source
            )
            ON CONFLICT (company_id) DO UPDATE SET
                legal_name = EXCLUDED.legal_name,
                cui        = EXCLUDED.cui,
                reg_com    = COALESCE(EXCLUDED.reg_com, company_billing_profiles.reg_com),
                address_line = COALESCE(EXCLUDED.address_line, company_billing_profiles.address_line),
                phone_billing = COALESCE(EXCLUDED.phone_billing, company_billing_profiles.phone_billing),
                vat_payer  = EXCLUDED.vat_payer,
                vat_cash   = EXCLUDED.vat_cash,
                e_invoice  = EXCLUDED.e_invoice,
                updated_from_anaf_at = EXCLUDED.updated_from_anaf_at,
                source = 'ANAF'
            """),
        {"cid": company_id, **data}
    )

def billing_ready(db: Session, base_cid: str, client_cid: str) -> tuple[bool, str]:
    # baza: profil + settings
    base_p = db.execute(text("SELECT 1 FROM company_billing_profiles WHERE company_id=:cid"), {"cid": base_cid}).scalar()
    base_s = db.execute(text("SELECT 1 FROM company_invoice_settings WHERE base_company_id=:cid"), {"cid": base_cid}).scalar()
    # client: profil
    client_p = db.execute(text("SELECT 1 FROM company_billing_profiles WHERE company_id=:cid"), {"cid": client_cid}).scalar()
    if not base_p:
        return False, "Completează profilul de facturare al BAZEI"
    if not base_s:
        return False, "Configurează setările de facturare (serie/număr) pentru BAZĂ"
    if not client_p:
        return False, "Completează profilul de facturare al CLIENTULUI"
    return True, ""
