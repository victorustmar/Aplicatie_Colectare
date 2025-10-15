import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CollectionOut } from "../types/api";

const nf2 = new Intl.NumberFormat("ro-RO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function toNum(x: number | string | null | undefined): number | null {
  if (x === null || x === undefined) return null;
  if (typeof x === "number") return x;
  const n = Number(x);
  return Number.isFinite(n) ? n : null;
}

export default function ClientCollections() {
  const [rows, setRows] = useState<CollectionOut[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const data = await api.listCollections();
        setRows(data);
      } catch (e: any) {
        setErr(e?.message || "Eroare la listare");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div style={{ maxWidth: 900, margin: "24px auto", padding: 16 }}>
      <h2>Colectările mele</h2>

      {loading && <div>Se încarcă…</div>}
      {err && <div style={{ color: "crimson" }}>{err}</div>}
      {!loading && !rows.length && <div className="muted">Nu există colectări încă.</div>}

      {!!rows.length && (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 6 }}>ID</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 6 }}>Status</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 6 }}>Baterii</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 6 }}>Greutate totală (kg)</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee", padding: 6 }}>Valoare totală (lei)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const w = toNum(r.total_weight);
              const c = toNum(r.total_cost);

              // Preferăm rezumatul calculat pe server; dacă lipsește, facem unul minimal din obiect
              const bateriiText =
                r.batteries_summary && r.batteries_summary.trim().length
                  ? r.batteries_summary
                  : Object.entries(r.batteries || {})
                      .map(([k, v]: any) => {
                        const pcs = v?.pcs ? `${v.pcs} buc` : null;
                        const kg = v?.weight_kg ? `${v.weight_kg} kg` : null;
                        const lei = v?.price_ron ? `${v.price_ron} lei` : null;
                        const parts = [pcs, kg, lei].filter(Boolean).join(", ");
                        return parts ? `${k}: ${parts}` : "";
                      })
                      .filter(Boolean)
                      .join("; ");

              const statusLabel = r.status === "VALIDATED" ? "Validată" : "În așteptare";

              return (
                <tr key={r.collection_id}>
                  <td style={{ padding: 6 }}>{r.collection_id}</td>
                  <td style={{ padding: 6 }}>{statusLabel}</td>
                  <td style={{ padding: 6 }}>{bateriiText || "-"}</td>
                  <td style={{ padding: 6 }}>{w !== null ? nf2.format(w) : "-"}</td>
                  <td style={{ padding: 6 }}>{c !== null ? nf2.format(c) : "-"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
