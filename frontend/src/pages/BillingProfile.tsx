import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import type { BillingProfile, BillingProfileUpdate } from "../types/api";

export default function BillingProfilePage() {
  const [profile, setProfile] = useState<BillingProfile | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try { setProfile(await api.getBillingProfile()); }
      catch (e: any) { setErr(e?.message || "Eroare la încărcarea profilului"); }
    })();
  }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;
    setErr(null); setOk(null);
    const payload: BillingProfileUpdate = {
      legal_name: profile.legal_name,
      reg_com: profile.reg_com || undefined,
      address_line: profile.address_line || undefined,
      city: profile.city || undefined,
      county: profile.county || undefined,
      postal_code: profile.postal_code || undefined,
      country: profile.country || undefined,
      bank_name: profile.bank_name || undefined,
      iban: profile.iban || undefined,
      email_billing: profile.email_billing || undefined,
      phone_billing: profile.phone_billing || undefined,
    };
    try {
      const res = await api.updateBillingProfile(payload);
      setProfile(res);
      setOk("Salvat.");
    } catch (e: any) {
      setErr(e?.message || "Eroare la salvare");
    }
  };

  if (!profile) return <div style={{ padding: 16 }}>{err || "Se încarcă…"}</div>;

  const set = (k: keyof BillingProfile, v: any) => setProfile({ ...(profile as any), [k]: v });

  return (
    <div style={{ maxWidth: 700, margin: "24px auto", padding: 16 }}>
      <h2>Profil de facturare</h2>
      {err && <div style={{ color: "crimson" }}>{err}</div>}
      {ok && <div style={{ color: "seagreen" }}>{ok}</div>}
      <form onSubmit={save} style={{ display: "grid", gap: 10, marginTop: 12 }}>
        <label>Denumire legală</label>
        <input value={profile.legal_name} onChange={e => set("legal_name", e.target.value)} />

        <label>Reg. Com.</label>
        <input value={profile.reg_com || ""} onChange={e => set("reg_com", e.target.value)} />

        <label>Adresă</label>
        <input value={profile.address_line || ""} onChange={e => set("address_line", e.target.value)} />

        <label>IBAN</label>
        <input value={profile.iban || ""} onChange={e => set("iban", e.target.value)} />

        <label>Bank</label>
        <input value={profile.bank_name || ""} onChange={e => set("bank_name", e.target.value)} />

        <label>Email facturare</label>
        <input value={profile.email_billing || ""} onChange={e => set("email_billing", e.target.value)} />

        <label>Telefon</label>
        <input value={profile.phone_billing || ""} onChange={e => set("phone_billing", e.target.value)} />

        <button type="submit">Salvează</button>
      </form>
    </div>
  );
}
