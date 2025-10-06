from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import get_db
from app.utils.security import get_current_user_claims
from app.schemas.billing import (
    BillingProfile, BillingProfileUpdate,
    InvoiceSettings, InvoiceSettingsUpdate
)
import json

router = APIRouter(prefix="/billing", tags=["billing"])

# ——— PROFIL FACTURARE ———

@router.get("/profile", response_model=BillingProfile)
def get_profile(claims = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    company_id = claims.get("company_id")
    if not company_id:
        raise HTTPException(403, "Utilizatorul nu este asociat unei companii")

    row = db.execute(
        text("""
        SELECT
          c.company_id,                                   -- stored as CHAR(36) in MySQL schema
          COALESCE(p.legal_name, c.name) AS legal_name,
          COALESCE(p.cui, c.cui) AS cui,
          p.reg_com, p.address_line, p.city, p.county, p.postal_code,
          COALESCE(p.country,'RO') AS country,
          p.bank_name, p.iban, p.email_billing, p.phone_billing,
          p.vat_payer, p.vat_cash, p.e_invoice,
          CAST(p.updated_from_anaf_at AS CHAR) AS updated_from_anaf_at,   -- <- make it a string for Pydantic
          COALESCE(p.source,'ANAF') AS source
        FROM companies c
        LEFT JOIN company_billing_profiles p ON p.company_id = c.company_id
        WHERE c.company_id = :cid
        """),
        {"cid": str(company_id)}
    ).mappings().first()

    if not row:
        raise HTTPException(404, "Compania nu există")
    return row

@router.put("/profile", response_model=BillingProfile)
def update_profile(payload: BillingProfileUpdate,
                   request: Request,
                   claims = Depends(get_current_user_claims),
                   db: Session = Depends(get_db)):
    company_id = claims.get("company_id")
    if not company_id:
        raise HTTPException(403, "Utilizatorul nu este asociat unei companii")

    comp = db.execute(
        text("SELECT name, cui FROM companies WHERE company_id=:cid"),
        {"cid": str(company_id)}
    ).mappings().first()
    if not comp:
        raise HTTPException(404, "Compania nu există")

    # MySQL upsert
    db.execute(
        text("""
        INSERT INTO company_billing_profiles(
            company_id, legal_name, cui, reg_com, address_line, city, county, postal_code,
            country, bank_name, iban, email_billing, phone_billing, source
        )
        VALUES(
            :cid, COALESCE(:legal_name, :fallback_name), :fallback_cui, :reg_com, :address_line, :city, :county, :postal_code,
            COALESCE(:country, 'RO'), :bank_name, :iban, :email_billing, :phone_billing, 'USER'
        )
        ON DUPLICATE KEY UPDATE
            legal_name   = COALESCE(VALUES(legal_name),   company_billing_profiles.legal_name),
            reg_com      = COALESCE(VALUES(reg_com),      company_billing_profiles.reg_com),
            address_line = COALESCE(VALUES(address_line), company_billing_profiles.address_line),
            city         = COALESCE(VALUES(city),         company_billing_profiles.city),
            county       = COALESCE(VALUES(county),       company_billing_profiles.county),
            postal_code  = COALESCE(VALUES(postal_code),  company_billing_profiles.postal_code),
            country      = COALESCE(VALUES(country),      company_billing_profiles.country),
            bank_name    = COALESCE(VALUES(bank_name),    company_billing_profiles.bank_name),
            iban         = COALESCE(VALUES(iban),         company_billing_profiles.iban),
            email_billing= COALESCE(VALUES(email_billing),company_billing_profiles.email_billing),
            phone_billing= COALESCE(VALUES(phone_billing),company_billing_profiles.phone_billing),
            source='USER'
        """),
        {
            "cid": str(company_id),
            "fallback_name": comp["name"],
            "fallback_cui": comp["cui"],
            **payload.model_dump()
        }
    )

    db.execute(
        text("""INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details)
                VALUES (:uid, :cid, 'BILLING_PROFILE_UPDATED', :d)"""),
        {"uid": str(claims.get("sub")), "cid": str(company_id),
         "d": json.dumps(payload.model_dump(exclude_none=True))}
    )
    db.commit()

    return get_profile(claims, db)

# ——— SETĂRI FACTURI (doar BASE) ———

@router.get("/settings", response_model=InvoiceSettings)
def get_settings(claims = Depends(get_current_user_claims), db: Session = Depends(get_db)):
    if claims.get("role") != "BASE":
        raise HTTPException(403, "Doar contul BASE are setări de facturare")
    base_company_id = str(claims.get("company_id"))

    row = db.execute(
        text("""
        SELECT base_company_id, series_code, next_number, year_reset, due_days, default_vat_rate
        FROM company_invoice_settings WHERE base_company_id=:cid
        """),
        {"cid": base_company_id}
    ).mappings().first()

    if not row:
        db.execute(
            text("""INSERT INTO company_invoice_settings(base_company_id)
                    VALUES (:cid)"""),
            {"cid": base_company_id}
        )
        db.commit()
        row = db.execute(
            text("""SELECT base_company_id, series_code, next_number, year_reset, due_days, default_vat_rate
                    FROM company_invoice_settings WHERE base_company_id=:cid"""),
            {"cid": base_company_id}
        ).mappings().first()

    return row

@router.put("/settings", response_model=InvoiceSettings)
def update_settings(payload: InvoiceSettingsUpdate,
                    claims = Depends(get_current_user_claims),
                    db: Session = Depends(get_db)):
    if claims.get("role") != "BASE":
        raise HTTPException(403, "Doar contul BASE poate modifica setările de facturare")
    cid = str(claims.get("company_id"))

    db.execute(
        text("""INSERT INTO company_invoice_settings(base_company_id)
                VALUES(:cid)
                ON DUPLICATE KEY UPDATE base_company_id=base_company_id"""),
        {"cid": cid}
    )

    payload_dict = payload.model_dump()

    if payload.next_number is not None:
        cur_next = db.execute(
            text("SELECT next_number FROM company_invoice_settings WHERE base_company_id=:cid"),
            {"cid": cid}
        ).scalar()
        if cur_next is not None and payload.next_number < int(cur_next):
            raise HTTPException(
                status_code=422,
                detail=f"next_number ({payload.next_number}) nu poate fi mai mic decât cel curent ({cur_next})"
            )

    db.execute(
        text("""
        UPDATE company_invoice_settings
           SET series_code       = COALESCE(:series_code, series_code),
               year_reset        = COALESCE(:year_reset, year_reset),
               due_days          = COALESCE(:due_days, due_days),
               default_vat_rate  = COALESCE(:default_vat_rate, default_vat_rate),
               next_number       = COALESCE(:next_number, next_number)
         WHERE base_company_id = :cid
        """),
        {"cid": cid, **payload_dict}
    )

    db.execute(
        text("""INSERT INTO audit_logs(actor_user_id, actor_company_id, action, details)
                VALUES (:uid, :cid, 'INVOICE_SETTINGS_UPDATED', :d)"""),
        {"uid": str(claims.get("sub")), "cid": cid, "d": json.dumps(payload.model_dump(exclude_none=True))}
    )
    db.commit()

    return get_settings(claims, db)
