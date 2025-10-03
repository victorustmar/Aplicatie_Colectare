import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CollectionOut } from "../types/api";

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
          <thead><tr>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>ID</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Status</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Baterii</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Greutate</th>
            <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Cost</th>
          </tr></thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.collection_id}>
                <td style={{ padding: 6 }}>{r.collection_id}</td>
                <td style={{ padding: 6 }}>{r.status}</td>
                <td style={{ padding: 6 }}>
                  {Object.keys(r.batteries || {}).map(k => `${k}:${r.batteries[k]}`).join(", ")}
                </td>
                <td style={{ padding: 6 }}>{r.total_weight ?? "-"}</td>
                <td style={{ padding: 6 }}>{r.total_cost ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
