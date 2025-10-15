import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { CollectionCreate } from "../types/api";
import { BATTERY_LABELS, BATTERY_SECTIONS, BATTERY_KEYS_ORDER } from "../lib/batteries";

type NumOrEmpty = number | "";
type BatteryLineState = { pcs: NumOrEmpty; weight_kg: NumOrEmpty; price_ron: NumOrEmpty };
type BatteriesState = Record<string, BatteryLineState>;

const nf2 = new Intl.NumberFormat("ro-RO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const toNum = (v: NumOrEmpty) => (v === "" ? 0 : Number(v));
const clean = (s: string) => s.trim().replace(",", ".");

export default function ClientAddCollection() {
  const nav = useNavigate();

  // stare inițială: toate câmpurile goale (nu afișăm zerouri)
  const [bats, setBats] = useState<BatteriesState>(() => {
    const init: BatteriesState = {};
    for (const k of BATTERY_KEYS_ORDER) init[k] = { pcs: "", weight_kg: "", price_ron: "" };
    return init;
  });

  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  // totaluri introduse
  const totals = useMemo(() => {
    let totalPcs = 0;
    let totalKg = 0;
    let totalLei = 0;
    for (const k of Object.keys(bats)) {
      totalPcs += toNum(bats[k].pcs);
      totalKg += toNum(bats[k].weight_kg);
      totalLei += toNum(bats[k].price_ron);
    }
    return { totalPcs, totalKg, totalLei };
  }, [bats]);

  const canSubmit = useMemo(() => {
    return Object.values(bats).some((ln) => toNum(ln.pcs) > 0 || toNum(ln.weight_kg) > 0 || toNum(ln.price_ron) > 0);
  }, [bats]);

  const onChangeInt = (key: string, val: string) => {
    const s = clean(val);
    if (s === "") return setBats((p) => ({ ...p, [key]: { ...p[key], pcs: "" } }));
    const n = Number(s);
    setBats((p) => ({ ...p, [key]: { ...p[key], pcs: !isFinite(n) || n < 0 ? "" : Math.floor(n) } }));
  };

  const onChangeFloat = (key: string, field: "weight_kg" | "price_ron", val: string) => {
    const s = clean(val);
    if (s === "") return setBats((p) => ({ ...p, [key]: { ...p[key], [field]: "" } }));
    const n = Number(s);
    setBats((p) => ({ ...p, [key]: { ...p[key], [field]: !isFinite(n) || n < 0 ? "" : n } }));
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    setOk(null);
    if (!canSubmit) {
      setErr("Completează cel puțin un rând cu valori > 0.");
      return;
    }
    setSaving(true);
    try {
      const batteries: CollectionCreate["batteries"] = {};
      for (const [k, ln] of Object.entries(bats)) {
        const pcs = toNum(ln.pcs);
        const weight_kg = toNum(ln.weight_kg);
        const price_ron = toNum(ln.price_ron);
        if (pcs > 0 || weight_kg > 0 || price_ron > 0) {
          batteries[k] = { pcs, weight_kg, price_ron };
        }
      }
      const payload: CollectionCreate = { batteries };
      await api.createCollection(payload);
      setOk("Colectarea a fost creată.");

      // reset formular
      const reset: BatteriesState = {};
      for (const k of BATTERY_KEYS_ORDER) reset[k] = { pcs: "", weight_kg: "", price_ron: "" };
      setBats(reset);

      // poți redirecționa dacă vrei:
      // nav("/client/collections");
    } catch (e: any) {
      setErr(e?.message || "Eroare la creare colectare");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: 980, margin: "24px auto", padding: 16 }}>
      <h2>Adaugă colectare</h2>

      <form onSubmit={submit} style={{ display: "grid", gap: 18, marginTop: 12 }}>
        {BATTERY_SECTIONS.map((section) => (
          <section key={section.id}>
            <h3>{section.title}</h3>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 6 }}>Tip</th>
                  <th style={{ textAlign: "center", borderBottom: "1px solid #eee", padding: 6 }}>Nr. bucăți</th>
                  <th style={{ textAlign: "center", borderBottom: "1px solid #eee", padding: 6 }}>Total greutate (kg)</th>
                  <th style={{ textAlign: "right", borderBottom: "1px solid #eee", padding: 6 }}>Valoare (lei)</th>
                </tr>
              </thead>
              <tbody>
                {section.keys.map((k) => {
                  const ln = bats[k];
                  return (
                    <tr key={k}>
                      <td style={{ padding: 6 }}>{BATTERY_LABELS[k] || k}</td>
                      <td style={{ textAlign: "center", padding: 6 }}>
                        <input
                          type="number"
                          min={0}
                          step={1}
                          placeholder="0"
                          value={ln.pcs === "" ? "" : ln.pcs}
                          onChange={(e) => onChangeInt(k, e.target.value)}
                          style={{ width: 120 }}
                        />
                      </td>
                      <td style={{ textAlign: "center", padding: 6 }}>
                        <input
                          type="number"
                          min={0}
                          step={0.01}
                          placeholder="0"
                          value={ln.weight_kg === "" ? "" : ln.weight_kg}
                          onChange={(e) => onChangeFloat(k, "weight_kg", e.target.value)}
                          style={{ width: 140 }}
                        />
                      </td>
                      <td style={{ textAlign: "right", padding: 6 }}>
                        <input
                          type="number"
                          min={0}
                          step={0.01}
                          placeholder="0"
                          value={ln.price_ron === "" ? "" : ln.price_ron}
                          onChange={(e) => onChangeFloat(k, "price_ron", e.target.value)}
                          style={{ width: 140, textAlign: "right" }}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        ))}

        {/* Totaluri introduse (doar informativ) */}
        <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
          <div>
            <strong>Total piese:</strong> {totals.totalPcs}
          </div>
          <div>
            <strong>Greutate totală:</strong> {nf2.format(totals.totalKg)} kg
          </div>
          <div>
            <strong>Valoare totală:</strong> {nf2.format(totals.totalLei)} lei
          </div>
        </div>

        {err && <div style={{ color: "crimson" }}>{err}</div>}
        {ok && <div style={{ color: "seagreen" }}>{ok}</div>}

        <div>
          <button disabled={!canSubmit || saving} type="submit">
            {saving ? "Se salvează…" : "Creează"}
          </button>
        </div>
      </form>
    </div>
  );
}
