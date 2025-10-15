import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import type { RecyclingOut } from "../types/api";

const fmt = (n?: number | string | null) => {
  if (n == null || n === "") return "-";
  const v = typeof n === "string" ? Number(n) : n;
  if (!Number.isFinite(v)) return "-";
  return v.toLocaleString("ro-RO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

export default function RecyclerRecyclings() {
  const [rows, setRows] = useState<RecyclingOut[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    setErr(null);
    try {
      setRows(await api.listRecyclings());
    } catch (e: any) {
      setErr(e?.message || "Eroare la listare");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <div style={{ maxWidth: 1000, margin: "24px auto", padding: 16 }}>
      <h2>Reciclări</h2>
      {loading && <div>Se încarcă…</div>}
      {err && <div style={{ color: "crimson", marginBottom: 8 }}>{err}</div>}

      {!!rows.length && (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Status</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Greutate</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Valoare</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.recycling_id}>
                <td style={{ padding: 6 }}>{r.status}</td>
                <td style={{ padding: 6 }}>{fmt(r.total_weight)}</td>
                <td style={{ padding: 6 }}>{fmt(r.total_cost)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {!loading && !rows.length && <div className="muted">Nu există reciclări.</div>}
    </div>
  );
}
