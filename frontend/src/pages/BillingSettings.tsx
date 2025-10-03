import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import type { InvoiceSettings, InvoiceSettingsUpdate } from "../types/api";

export default function BillingSettingsPage() {
  const [sett, setSett] = useState<InvoiceSettings | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try { setSett(await api.getInvoiceSettings()); }
      catch (e: any) { setErr(e?.message || "Eroare la citire setări"); }
    })();
  }, []);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sett) return;
    setErr(null); setOk(null);
    const payload: InvoiceSettingsUpdate = {
      series_code: sett.series_code,
      year_reset: sett.year_reset,
      due_days: sett.due_days,
      default_vat_rate: sett.default_vat_rate,
      next_number: sett.next_number, // backend blochează scăderea
    };
    try {
      const res = await api.updateInvoiceSettings(payload);
      setSett(res);
      setOk("Salvat.");
    } catch (e: any) {
      setErr(e?.message || "Eroare la salvare setări");
    }
  };

  if (!sett) return <div style={{ padding: 16 }}>{err || "Se încarcă…"}</div>;
  const set = (k: keyof InvoiceSettings, v: any) => setSett({ ...(sett as any), [k]: v });

  return (
    <div style={{ maxWidth: 700, margin: "24px auto", padding: 16 }}>
      <h2>Setări facturi (BASE)</h2>
      {err && <div style={{ color: "crimson" }}>{err}</div>}
      {ok && <div style={{ color: "seagreen" }}>{ok}</div>}
      <form onSubmit={save} style={{ display: "grid", gap: 10, marginTop: 12 }}>
        <label>Serie</label>
        <input value={sett.series_code} onChange={e => set("series_code", e.target.value)} />
        <label>Următorul număr</label>
        <input type="number" value={sett.next_number} onChange={e => set("next_number", Number(e.target.value))} />
        <label>Resetare anuală</label>
        <input type="checkbox" checked={sett.year_reset} onChange={e => set("year_reset", e.target.checked)} />
        <label>Zile scadență</label>
        <input type="number" value={sett.due_days} onChange={e => set("due_days", Number(e.target.value))} />
        <label>TVA implicit (%)</label>
        <input type="number" value={sett.default_vat_rate} onChange={e => set("default_vat_rate", Number(e.target.value))} />

        <button type="submit">Salvează</button>
      </form>
    </div>
  );
}
