// import React, { useMemo, useState } from "react";
// import { useNavigate } from "react-router-dom";
// import { api } from "../api/client";
// import type { CollectionCreate } from "../types/api";
// import {
//   PORTABLE_KEYS, KG_KEYS, LABELS,
//   PORTABLE_RATES, PORTABLE_WEIGHTS_KG, KG_RATES,
// } from "../features/rates";

// type NumOrEmpty = number | "";
// type BatteriesState = Record<string, NumOrEmpty>;
// const round2 = (n: number) => Math.round(n * 100) / 100;
// const num = (v: NumOrEmpty) => (v === "" ? 0 : v); // normalize for math

// export default function ClientAddCollection() {
//   const nav = useNavigate();

//   // start empty (no 0s shown)
//   const [bats, setBats] = useState<BatteriesState>(() => {
//     const init: BatteriesState = {};
//     [...PORTABLE_KEYS, ...KG_KEYS].forEach(k => (init[k] = ""));
//     return init;
//   });

//   const [saving, setSaving] = useState(false);
//   const [err, setErr] = useState<string | null>(null);
//   const [ok, setOk] = useState<string | null>(null);

//   // live preview
//   const { subtotal, totalWeight } = useMemo(() => {
//     let sub = 0;
//     let kg  = 0;

//     // portable (buc)
//     for (const k of PORTABLE_KEYS) {
//       const qty = num(bats[k]);
//       if (qty > 0) {
//         sub += qty * PORTABLE_RATES[k];
//         kg  += qty * PORTABLE_WEIGHTS_KG[k];
//       }
//     }
//     // auto/industrial (kg)
//     for (const k of KG_KEYS) {
//       const w = num(bats[k]);
//       if (w > 0) {
//         sub += w * KG_RATES[k];
//         kg  += w;
//       }
//     }
//     return { subtotal: round2(sub), totalWeight: round2(kg) };
//   }, [bats]);

//   const canSubmit = useMemo(
//     () => Object.values(bats).some(v => Number(v) > 0),
//     [bats]
//   );

//   const onChangeInt = (key: string, val: string) => {
//     const s = val.trim();
//     if (s === "") { setBats(p => ({ ...p, [key]: "" })); return; }
//     const n = Number(s.replace(",", "."));
//     setBats(p => ({ ...p, [key]: !isFinite(n) || n < 0 ? "" : Math.floor(n) }));
//   };

//   const onChangeFloat = (key: string, val: string) => {
//     const s = val.trim();
//     if (s === "") { setBats(p => ({ ...p, [key]: "" })); return; }
//     const n = Number(s.replace(",", "."));
//     setBats(p => ({ ...p, [key]: !isFinite(n) || n < 0 ? "" : n }));
//   };

//   const submit = async (e: React.FormEvent) => {
//     e.preventDefault();
//     setErr(null); setOk(null);
//     if (!canSubmit) { setErr("Completează cel puțin o cantitate > 0."); return; }

//     setSaving(true);
//     try {
//       const payload: CollectionCreate = {
//         batteries: Object.fromEntries(
//           Object.entries(bats).filter(([, v]) => Number(v) > 0)
//             .map(([k, v]) => [k, Number(v)])
//         ),
//       };
//       await api.createCollection(payload);
//       setOk("Colectarea a fost creată.");

//       // reset to empty (not zeros)
//       const reset: BatteriesState = {};
//       [...PORTABLE_KEYS, ...KG_KEYS].forEach(k => (reset[k] = ""));
//       setBats(reset);

//       // nav("/client/collections"); // dacă vrei redirect
//     } catch (e: any) {
//       setErr(e?.message || "Eroare la creare colectare");
//     } finally {
//       setSaving(false);
//     }
//   };

//   return (
//     <div style={{ maxWidth: 980, margin: "24px auto", padding: 16 }}>
//       <h2>Adaugă colectare</h2>
//       <form onSubmit={submit} style={{ display: "grid", gap: 18, marginTop: 12 }}>
//         {/* Portable */}
//         <section>
//           <h3>Baterii portabile (buc)</h3>
//           <table style={{ width: "100%", borderCollapse: "collapse" }}>
//             <thead>
//               <tr>
//                 <th style={{ textAlign: "left" }}>Tip</th>
//                 <th>Tarif (lei/buc)</th>
//                 <th>Greutate (kg/buc)</th>
//                 <th style={{ width: 160 }}>Cantitate</th>
//               </tr>
//             </thead>
//             <tbody>
//               {PORTABLE_KEYS.map(k => (
//                 <tr key={k}>
//                   <td>{LABELS[k]}</td>
//                   <td style={{ textAlign: "center" }}>{PORTABLE_RATES[k]}</td>
//                   <td style={{ textAlign: "center" }}>{PORTABLE_WEIGHTS_KG[k]}</td>
//                   <td style={{ textAlign: "center" }}>
//                     <input
//                       type="number"
//                       min={0}
//                       step={1}
//                       placeholder="0"
//                       value={bats[k] === "" ? "" : bats[k]}
//                       onChange={e => onChangeInt(k, e.target.value)}
//                       style={{ width: 120 }}
//                     />
//                   </td>
//                 </tr>
//               ))}
//             </tbody>
//           </table>
//         </section>

//         {/* Auto & Industrial */}
//         <section>
//           <h3>Baterii auto și industriale (kg)</h3>
//           <table style={{ width: "100%", borderCollapse: "collapse" }}>
//             <thead>
//               <tr>
//                 <th style={{ textAlign: "left" }}>Tip</th>
//                 <th>Tarif (lei/kg)</th>
//                 <th style={{ width: 160 }}>Cantitate (kg)</th>
//               </tr>
//             </thead>
//             <tbody>
//               {KG_KEYS.map(k => (
//                 <tr key={k}>
//                   <td>{LABELS[k]}</td>
//                   <td style={{ textAlign: "center" }}>{KG_RATES[k]}</td>
//                   <td style={{ textAlign: "center" }}>
//                     <input
//                       type="number"
//                       min={0}
//                       step={0.01}
//                       placeholder="0"
//                       value={bats[k] === "" ? "" : bats[k]}
//                       onChange={e => onChangeFloat(k, e.target.value)}
//                       style={{ width: 120 }}
//                     />
//                   </td>
//                 </tr>
//               ))}
//             </tbody>
//           </table>
//         </section>

//         <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
//           <div><strong>Greutate totală estimată:</strong> {totalWeight} kg</div>
//           <div><strong>Subtotal estimat:</strong> {subtotal} lei</div>
//         </div>

//         {err && <div style={{ color: "crimson" }}>{err}</div>}
//         {ok && <div style={{ color: "seagreen" }}>{ok}</div>}

//         <div>
//           <button disabled={!canSubmit || saving} type="submit">
//             {saving ? "Se salvează…" : "Creează"}
//           </button>
//         </div>
//       </form>
//     </div>
//   );
// }

import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { CollectionCreate } from "../types/api";
import {
  PORTABLE_KEYS, KG_KEYS, LABELS,
  PORTABLE_RATES, PORTABLE_WEIGHTS_KG, KG_RATES,
} from "../features/rates";

type NumOrEmpty = number | "";
type BatteriesState = Record<string, NumOrEmpty>;

const round2 = (n: number) => Math.round(n * 100) / 100;
const num = (v: NumOrEmpty) => (v === "" ? 0 : v);
const fmt = (n: number) =>
  n === 0 ? "" : n.toLocaleString("ro-RO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function ClientAddCollection() {
  const nav = useNavigate();

  // inputs start empty (no zeros shown)
  const [bats, setBats] = useState<BatteriesState>(() => {
    const init: BatteriesState = {};
    [...PORTABLE_KEYS, ...KG_KEYS].forEach(k => (init[k] = ""));
    return init;
  });

  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  // line totals + category subtotals + overall totals
  const calc = useMemo(() => {
    let totalWeight = 0;
    let portableSubtotal = 0;
    let kgSubtotal = 0;
    const lineTotals: Record<string, number> = {};

    for (const k of PORTABLE_KEYS) {
      const qty = num(bats[k]);
      const value = qty * PORTABLE_RATES[k];
      const w = qty * PORTABLE_WEIGHTS_KG[k];
      lineTotals[k] = round2(value);
      totalWeight += w;
      portableSubtotal += value;
    }
    for (const k of KG_KEYS) {
      const w = num(bats[k]);
      const value = w * KG_RATES[k];
      lineTotals[k] = round2(value);
      totalWeight += w;
      kgSubtotal += value;
    }
    portableSubtotal = round2(portableSubtotal);
    kgSubtotal = round2(kgSubtotal);
    const subtotal = round2(portableSubtotal + kgSubtotal);
    totalWeight = round2(totalWeight);

    return { lineTotals, portableSubtotal, kgSubtotal, subtotal, totalWeight };
  }, [bats]);

  const canSubmit = useMemo(
    () => Object.values(bats).some(v => Number(v) > 0),
    [bats]
  );

  const onChangeInt = (key: string, val: string) => {
    const s = val.trim();
    if (s === "") { setBats(p => ({ ...p, [key]: "" })); return; }
    const n = Number(s.replace(",", "."));
    setBats(p => ({ ...p, [key]: !isFinite(n) || n < 0 ? "" : Math.floor(n) }));
  };

  const onChangeFloat = (key: string, val: string) => {
    const s = val.trim();
    if (s === "") { setBats(p => ({ ...p, [key]: "" })); return; }
    const n = Number(s.replace(",", "."));
    setBats(p => ({ ...p, [key]: !isFinite(n) || n < 0 ? "" : n }));
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null); setOk(null);
    if (!canSubmit) { setErr("Completează cel puțin o cantitate > 0."); return; }

    setSaving(true);
    try {
      const payload: CollectionCreate = {
        batteries: Object.fromEntries(
          Object.entries(bats)
            .filter(([, v]) => Number(v) > 0)
            .map(([k, v]) => [k, Number(v)])
        ),
      };
      await api.createCollection(payload);
      setOk("Colectarea a fost creată.");

      // reset to empty (not zeros)
      const reset: BatteriesState = {};
      [...PORTABLE_KEYS, ...KG_KEYS].forEach(k => (reset[k] = ""));
      setBats(reset);

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
        {/* Portable */}
        <section>
          <h3>Baterii portabile (buc)</h3>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>Tip</th>
                <th>Tarif (lei/buc)</th>
                <th>Greutate (kg/buc)</th>
                <th style={{ width: 160 }}>Cantitate</th>
                <th style={{ width: 140 }}>Valoare (lei)</th>
              </tr>
            </thead>
            <tbody>
              {PORTABLE_KEYS.map(k => (
                <tr key={k}>
                  <td>{LABELS[k]}</td>
                  <td style={{ textAlign: "center" }}>{PORTABLE_RATES[k]}</td>
                  <td style={{ textAlign: "center" }}>{PORTABLE_WEIGHTS_KG[k]}</td>
                  <td style={{ textAlign: "center" }}>
                    <input
                      type="number"
                      min={0}
                      step={1}
                      placeholder="0"
                      value={bats[k] === "" ? "" : bats[k]}
                      onChange={e => onChangeInt(k, e.target.value)}
                      style={{ width: 120 }}
                    />
                  </td>
                  <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                    {fmt(calc.lineTotals[k] || 0)}
                  </td>
                </tr>
              ))}
              {/* Subtotal portabile */}
              <tr style={{ background: "#fafafa", fontWeight: 600 }}>
                <td colSpan={4} style={{ textAlign: "right", paddingRight: 8 }}>Subtotal portabile</td>
                <td style={{ textAlign: "right" }}>{fmt(calc.portableSubtotal)} lei</td>
              </tr>
            </tbody>
          </table>
        </section>

        {/* Auto & Industrial */}
        <section>
          <h3>Baterii auto și industriale (kg)</h3>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>Tip</th>
                <th>Tarif (lei/kg)</th>
                <th style={{ width: 160 }}>Cantitate (kg)</th>
                <th style={{ width: 140 }}>Valoare (lei)</th>
              </tr>
            </thead>
            <tbody>
              {KG_KEYS.map(k => (
                <tr key={k}>
                  <td>{LABELS[k]}</td>
                  <td style={{ textAlign: "center" }}>{KG_RATES[k]}</td>
                  <td style={{ textAlign: "center" }}>
                    <input
                      type="number"
                      min={0}
                      step={0.01}
                      placeholder="0"
                      value={bats[k] === "" ? "" : bats[k]}
                      onChange={e => onChangeFloat(k, e.target.value)}
                      style={{ width: 120 }}
                    />
                  </td>
                  <td style={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                    {fmt(calc.lineTotals[k] || 0)}
                  </td>
                </tr>
              ))}
              {/* Subtotal auto/industriale */}
              <tr style={{ background: "#fafafa", fontWeight: 600 }}>
                <td colSpan={3} style={{ textAlign: "right", paddingRight: 8 }}>Subtotal auto & industriale</td>
                <td style={{ textAlign: "right" }}>{fmt(calc.kgSubtotal)} lei</td>
              </tr>
            </tbody>
          </table>
        </section>

        {/* Totals */}
        <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
          <div><strong>Greutate totală estimată:</strong> {fmt(calc.totalWeight)} kg</div>
          <div><strong>Subtotal estimat (total):</strong> {fmt(calc.subtotal)} lei</div>
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
