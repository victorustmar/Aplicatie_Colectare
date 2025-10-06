import React, { useEffect, useState } from "react";
import { api } from "../api/client";
import type { CollectionOut } from "../types/api";
import { useNavigate } from "react-router-dom";
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
    <div style={{ maxWidth: 1000, margin: "24px auto", padding: 16 }}>
      <h2>Colectări clienți</h2>
      {loading && <div>Se încarcă…</div>}
      {err && <div style={{ color: "crimson", marginBottom: 8 }}>{err}</div>}

      {!!rows.length && (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 12 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Client</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Greutate</th>
              <th style={{ textAlign: "left", borderBottom: "1px solid #eee" }}>Cost</th>
              {/* slim actions col (only shows button for PENDING) */}
              <th style={{ width: 120, borderBottom: "1px solid #eee" }} />
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r.collection_id}>
                <td style={{ padding: 6 }}>{r.client_name || r.client_company_id}</td>
                <td style={{ padding: 6 }}>{r.total_weight ?? "-"}</td>
                <td style={{ padding: 6 }}>{r.total_cost ?? "-"}</td>
                <td style={{ padding: 6, textAlign: "right" }}>
                  {r.status === "PENDING" ? (
                    <button onClick={() => nav(`/collections/${r.collection_id}/review`)}>
                      Validează
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {!loading && !rows.length && <div className="muted">Nu există colectări.</div>}
    </div>
  );
}