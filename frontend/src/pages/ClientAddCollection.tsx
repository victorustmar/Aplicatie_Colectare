import React, { useState } from "react";
import { api } from "../api/client";
import type { CollectionCreate } from "../types/api";

export default function ClientAddCollection() {
  const [tip1, setTip1] = useState<number>(0);
  const [tip2, setTip2] = useState<number>(0);
  const [totalWeight, setTotalWeight] = useState<number | "">("");
  const [totalCost, setTotalCost] = useState<number | "">("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null); setOk(null); setLoading(true);
    const payload: CollectionCreate = {
      batteries: {
        ...(tip1 ? { tip1 } : {}),
        ...(tip2 ? { tip2 } : {}),
      },
      total_weight: totalWeight === "" ? undefined : Number(totalWeight),
      total_cost: totalCost === "" ? undefined : Number(totalCost),
    };
    try {
      await api.createCollection(payload);
      setOk("Colectarea a fost creată.");
      setTip1(0); setTip2(0); setTotalWeight(""); setTotalCost("");
    } catch (e: any) {
      setErr(e?.message || "Eroare la creare colectare");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 520, margin: "24px auto", padding: 16 }}>
      <h2>Adaugă colectare</h2>
      <form onSubmit={submit} style={{ display: "grid", gap: 12, marginTop: 12 }}>
        <label>Tip1 (buc)</label>
        <input type="number" value={tip1} min={0} onChange={e => setTip1(Number(e.target.value))} />
        <label>Tip2 (buc)</label>
        <input type="number" value={tip2} min={0} onChange={e => setTip2(Number(e.target.value))} />
        <label>Greutate totală (kg)</label>
        <input type="number" value={totalWeight} onChange={e => setTotalWeight(e.target.value === "" ? "" : Number(e.target.value))} />
        <label>Cost total (RON)</label>
        <input type="number" value={totalCost} onChange={e => setTotalCost(e.target.value === "" ? "" : Number(e.target.value))} />
        {err && <div style={{ color: "crimson" }}>{err}</div>}
        {ok && <div style={{ color: "seagreen" }}>{ok}</div>}
        <button disabled={loading} type="submit">{loading ? "Se salvează…" : "Creează"}</button>
      </form>
    </div>
  );
}
