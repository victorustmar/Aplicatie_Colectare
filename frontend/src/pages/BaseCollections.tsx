import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CollectionOut } from "../types/api";
import { useNavigate } from "react-router-dom";

const nf2 = new Intl.NumberFormat("ro-RO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function toNum(x: number | string | null | undefined): number | null {
  if (x === null || x === undefined) return null;
  if (typeof x === "number") return Number.isFinite(x) ? x : null;
  const n = Number(x);
  return Number.isFinite(n) ? n : null;
}

export default function BaseCollections() {
  const [rows, setRows] = useState<CollectionOut[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  const load = async () => {
    setLoading(true); setErr(null);
    try { setRows(await api.listCollections()); }
    catch (e: any) { setErr(e?.message || "Eroare la listare"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  return (
    <div style={{ maxWidth: 1100, margin: "24px auto", padding: 16 }}>
      <h2>Colectări clienți</h2>

      {loading && <div>Se încarcă…</div>}
      {err && <div style={{ color: "crimson", marginBottom: 8 }}>{err}</div>}

      {!!rows.length && (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 6 }}>Client</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 6 }}>Baterii</th>
              <th style={{ textAlign: "right", borderBottom: "1px solid #eee", padding: 6 }}>Greutate totală (kg)</th>
              <th style={{ textAlign: "right", borderBottom: "1px solid #eee", padding: 6 }}>Valoare totală (lei)</th>
              {/* col. acțiuni (buton doar pentru PENDING) */}
              <th style={{ width: 140, borderBottom: "1px solid #eee" }} />
            </tr>
          </thead>
          <tbody>
            {rows.map(r => {
              const w = toNum(r.total_weight);
              const c = toNum(r.total_cost);
              const bateriiText =
                r.batteries_summary && r.batteries_summary.trim().length
                  ? r.batteries_summary
                  : Object.entries((r as any).batteries || {})
                      .map(([k, v]: any) => {
                        const pcs = v?.pcs ? `${v.pcs} buc` : null;
                        const kg = v?.weight_kg ? `${v.weight_kg} kg` : null;
                        const lei = v?.price_ron ? `${v.price_ron} lei` : null;
                        const parts = [pcs, kg, lei].filter(Boolean).join(", ");
                        return parts ? `${k}: ${parts}` : "";
                      })
                      .filter(Boolean)
                      .join("; ");

              return (
                <tr key={r.collection_id}>
                  <td style={{ padding: 6 }}>{r.client_name || r.client_company_id}</td>
                  <td style={{ padding: 6 }}>{bateriiText || "-"}</td>
                  <td style={{ padding: 6, textAlign: "right" }}>{w !== null ? nf2.format(w) : "-"}</td>
                  <td style={{ padding: 6, textAlign: "right" }}>{c !== null ? nf2.format(c) : "-"}</td>
                  <td style={{ padding: 6, textAlign: "right" }}>
                    {r.status === "PENDING" ? (
                      <button onClick={() => nav(`/collections/${r.collection_id}/review`)}>
                        Validează
                      </button>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {!loading && !rows.length && <div className="muted">Nu există colectări.</div>}
    </div>
  );
}
